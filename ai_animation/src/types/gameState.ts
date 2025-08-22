import { z } from 'zod';
import { PowerENUM, PowerENUMSchema } from './map';
import { OrderFromString } from './unitOrders';
import { ProvinceENUMSchema } from './map';

// Define the possible relationship statuses
const RelationshipStatusSchema = z.enum([
  "Enemy",
  "Unfriendly",
  "Neutral",
  "Friendly",
  "Ally"
]);

const MessageSchema = z.object({
  sender: PowerENUMSchema,
  recipient: PowerENUMSchema,
  time_sent: z.number(),
  phase: z.string(),
  message: z.string()
})
const PhaseSchema = z.object({
  messages: z.array(MessageSchema),
  name: z.string(),
  orders: z.record(PowerENUMSchema, z.array(OrderFromString).nullable()),
  results: z.record(z.string(), z.array(z.any())).transform((originalResults) => {
    // Transform results from {"A BUD": [results]} to {A: {"BUD": [results]}, F: {"BUD": [results]}}
    const transformed: { A: Record<string, any[]>, F: Record<string, any[]> } = { A: {}, F: {} };

    for (const [key, value] of Object.entries(originalResults)) {
      const tokens = key.split(' ');
      if (tokens.length >= 2) {
        const unitType = tokens[0]; // "A" or "F"
        const province = tokens[1].split('/')[0]; // Remove coast specification if present

        if (unitType === 'A' || unitType === 'F') {
          if (!transformed[unitType as 'A' | 'F']) {
            transformed[unitType as 'A' | 'F'] = {};
          }
          transformed[unitType as 'A' | 'F'][province] = value;
        }
      }
    }

    return transformed;
  }),
  state: z.object({
    units: z.record(PowerENUMSchema, z.array(z.string())),
    centers: z.record(PowerENUMSchema, z.array(ProvinceENUMSchema)),
    homes: z.record(PowerENUMSchema, z.array(z.string())),
    influence: z.record(PowerENUMSchema, z.array(ProvinceENUMSchema)),
  }),
  year: z.number().optional(),
  summary: z.string().optional(),
  // Add agent_relationships based on the provided lmvsgame.json structure
  agent_relationships: z.record(
    PowerENUMSchema,
    z.record(PowerENUMSchema, RelationshipStatusSchema)
  ).optional(),
});

export const GameSchema = z.object({
  map: z.string(),
  id: z.string(),
  power: PowerENUMSchema.optional(),
  phases: z.array(PhaseSchema),
});

export type GamePhase = z.infer<typeof PhaseSchema>;
export type GameSchemaType = z.infer<typeof GameSchema>;
export type MessageSchemaType = z.infer<typeof MessageSchema>
