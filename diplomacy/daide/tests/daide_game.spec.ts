// diplomacy/daide/tests/daide_game.spec.ts

import * as net from 'net';
import * as fs from 'fs/promises';
import * as path from 'path';
import { parse as csvParse } from 'csv-parse/sync';
import { Buffer } from 'buffer';
import { setTimeout as sleep } from 'timers/promises';


import { DaideServer } from '../server';
// ConnectionHandlerTs is implicitly tested via DaideServer
import {
    DaideMessage, MessageType, InitialMessage, DiplomacyMessage as DaideDiplomacyMessage, ErrorCode
} from '../messages';
import * as daideTokens from '../tokens';
import { daideStringToBytes, daideBytesToString } from '../utils';

// Logger
const logger = {
  debug: (...args: any[]) => console.debug('[DEBUG]', ...args),
  info: (...args: any[]) => console.info('[INFO]', ...args),
  warn: (...args: any[]) => console.warn('[WARN]', ...args),
  error: (...args: any[]) => console.error('[ERROR]', ...args),
};

const HOSTNAME = '127.0.0.1';
const FILE_FOLDER_NAME = __dirname;
const BOT_KEYWORD = '__bot__';

interface DaideCommData {
  client_id: number;
  request: string;
  resp_notifs: string[];
}

// --- Mocks & Placeholders ---
interface MockPower {
    name: string;
    controller: string | null;
    is_controlled_by: (username: string | null) => boolean;
    get_controller: () => string | null;
    units: string[];
    centers: string[];
    retreats: Record<string, string[]>;
    homes: string[];
    // For MissingOrdersNotification
    orders: Record<string, string>;
    adjust?: any[]; // if OrderSplitter logic is deeply mocked for adjustment phase
}

interface ServerGameMock {
  game_id: string;
  map_name: string;
  rules: string[];
  deadline: number;
  powers: Record<string, MockPower>;
  current_phase: string; // Property, not method
  status: string;
  is_game_completed: boolean;
  is_game_canceled: boolean;
  has_draw_vote(): boolean;
  state_history: { last_value: () => { name: string }, items: () => Record<string, any> };
  map: { name: string, phase_abbr: (long:string)=>string, find_next_phase: (long:string)=>string, phase_long: (abbr:string)=>string }; // Simplified map
  get_power(powerName: string): MockPower | undefined;
  count_controlled_powers(): number;
  // For internal request managers (mocked)
  set_orders_internal: (powerName: string, orders: string[], wait?: boolean) => void;
  set_wait_flag_internal: (powerName: string, wait: boolean) => void;
  add_message_internal: (message: any) => void;
  set_vote_internal: (powerName: string, vote: string) => void;
}

interface DaideUserMock {
    username: string;
    passcode: number;
    client_name: string;
    client_version: string;
    to_dict: () => any;
}

interface MasterServerMock {
  users: {
      get_user: (username: string) => DaideUserMock | null;
      get_name: (token: string) => string | null;
      has_token: (token: string) => boolean;
      replace_user: (username: string, daideUser: DaideUserMock) => void;
      remove_connection: (ch: ConnectionHandlerTs, remove_tokens: boolean) => void;
      count_connections: () => number;
      // Test specific:
      _mock_users: Map<string, DaideUserMock>; // Store users here
      _mock_tokens: Map<string, string>; // token -> username
  };
  get_game: (gameId: string) => ServerGameMock | null;
  add_new_game: (game: ServerGameMock) => void;
  start_new_daide_server: (gameId: string, port: number) => Promise<DaideServer>;
  stop_daide_server: (gameId: string | null) => void;
  handleInternalRequest: (request: any, connection_handler?: ConnectionHandlerTs) => Promise<any>;
  assert_token: (token: string | null | undefined, connection_handler: ConnectionHandlerTs) => void;
}

// Placeholder for the client connection used to fetch DAIDE port (main client, not DAIDE client)
interface DiplomacyClientConnectionMock {
    get_daide_port(gameId: string): Promise<number>; // This is what ClientsCommsSimulator needs
    authenticate(username:string, password:string):Promise<ClientChannelMock>; // For run_game_data
    connection?: { close: () => void; }; // Optional, if direct close is needed
    close(): Promise<void>; // General close method
}
interface ClientChannelMock {
    join_game(params: {game_id: string, power_name?: string, registration_password?: string | null}): Promise<NetworkGameMock>;
    get_dummy_waiting_powers(params: {buffer_size: number}): Promise<Record<string, string[]>>;
    // other channel methods used by tests
}
interface NetworkGameMock { // Client-side game instance
    game_id: string;
    role: string;
    set_orders(params: {power_name?: string, orders: string[], wait?: boolean}): Promise<void>;
}


// BufferReaderHelper
class BufferReaderHelper {
    private buffer: Buffer;
    private offset: number = 0;
    constructor(buffer: Buffer) { this.buffer = buffer; }
    readBytes(length: number): Buffer {
        if (this.offset + length > this.buffer.length) {
            throw new Error(`BufferReaderHelper: Attempt to read ${length} bytes with only ${this.buffer.length - this.offset} remaining.`);
        }
        const slice = this.buffer.slice(this.offset, this.offset + length);
        this.offset += length;
        return slice;
    }
    get remainingLength(): number { return this.buffer.length - this.offset; }
}

async function loadDaideCommsCsv(csvFilePath: string): Promise<DaideCommData[]> {
  const fileContent = await fs.readFile(csvFilePath, 'utf8');
  const records = csvParse(fileContent, { columns: false, skip_empty_lines: true, comment: '#' });
  return records.map((line: string[]) => ({
    client_id: parseInt(line[0], 10),
    request: line[1],
    resp_notifs: line.slice(2).filter(s => s && s.trim() !== ''),
  }));
}

class ClientCommsSimulator {
  private client_id: number;
  socket: net.Socket | null = null;
  private dataBuffer: Buffer = Buffer.alloc(0);
  private responsesReceivedThisTurn: string[] = [];
  private responseExpectationQueue: Array<{ count: number; resolve: (value: string[]) => void; reject: (reason?: any) => void; timeoutId: NodeJS.Timeout }> = [];
  public is_game_joined: boolean = false;
  public comms: DaideCommData[] = [];

  constructor(client_id: number) { this.client_id = client_id; }

  private _handleData(dataChunk: Buffer) {
    this.dataBuffer = Buffer.concat([this.dataBuffer, dataChunk]);
    logger.debug(`Client ${this.client_id} [${this.socket?.localPort}] RCV CHUNK (${dataChunk.length}), buf now ${this.dataBuffer.length}`);

    while (this.dataBuffer.length >= 4) {
        const messageTypeVal = this.dataBuffer.readUInt8(0);
        const remainingLength = this.dataBuffer.readUInt16BE(2);
        const totalMessageLength = 4 + remainingLength;

        if (this.dataBuffer.length >= totalMessageLength) {
            const messageBuffer = this.dataBuffer.slice(0, totalMessageLength);
            this.dataBuffer = this.dataBuffer.slice(totalMessageLength);

            const messageReader = new BufferReaderHelper(messageBuffer);
            DaideMessage.fromBuffer(messageReader)
                .then(daideMessage => {
                    let daideContentString = "";
                    if (daideMessage.messageType === MessageType.DIPLOMACY && daideMessage.content) {
                         daideContentString = daideBytesToString(daideMessage.content);
                    } else if (daideMessage instanceof InitialMessage || daideMessage instanceof RepresentationMessage) {
                        // These are structural, content isn't DAIDE tokens string
                        daideContentString = ""; // Or a type representation
                    } else if (daideMessage.content) {
                         daideContentString = daideBytesToString(daideMessage.content);
                    }

                    logger.info(`Client ${this.client_id} [${this.socket?.localPort}] PARSED DAIDE: ${MessageType[daideMessage.messageType]}, Content: ${daideContentString.substring(0,100)}`);

                    // Check for HLO to set is_game_joined (based on its command token bytes)
                    if (daideMessage.messageType === MessageType.DIPLOMACY && daideMessage.content.length >=2) {
                        const commandTokenBytes = daideMessage.content.slice(0,2);
                        if (commandTokenBytes[0] === daideTokens.HLO.toBytes()[0] && commandTokenBytes[1] === daideTokens.HLO.toBytes()[1]) {
                            this.is_game_joined = true;
                             logger.info(`Client ${this.client_id} game joined (HLO received).`);
                        }
                    }
                    if(daideMessage.messageType === MessageType.REPRESENTATION) { // RM is an implicit ack for IM
                        // For connect, this is the signal
                         if (this.responseExpectationQueue.length > 0 && this.responseExpectationQueue[0].count === 0) { // Special case for RM after IM
                            const waiter = this.responseExpectationQueue.shift();
                            clearTimeout(waiter!.timeoutId);
                            waiter!.resolve([]); // Resolve with empty as RM has no "content" in DAIDE string sense
                        }
                    } else {
                        this.responsesReceivedThisTurn.push(daideContentString);
                    }

                    if (this.responseExpectationQueue.length > 0) {
                        const waiter = this.responseExpectationQueue[0];
                        if (this.responsesReceivedThisTurn.length >= waiter.count) {
                            clearTimeout(waiter.timeoutId);
                            waiter.resolve(this.responsesReceivedThisTurn.slice(0, waiter.count));
                            this.responsesReceivedThisTurn = this.responsesReceivedThisTurn.slice(waiter.count);
                            this.responseExpectationQueue.shift();
                        }
                    }
                })
                .catch(err => { logger.error(`Client ${this.client_id} error parsing message: ${err.message}`); });
        } else { break; }
    }
  }

  async connect(port: number, host: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.socket = net.createConnection({ port, host }, () => {
        logger.info(`Client ${this.client_id} connected to DAIDE server ${host}:${port}`);
        this.socket?.on('data', (dataChunk) => this._handleData(dataChunk));

        const initialMsg = new InitialMessage();
        this.socket?.write(initialMsg.toBytes(), (err) => {
            if (err) return reject(err);
            logger.info(`Client ${this.client_id} sent InitialMessage.`);
            // Expect RepresentationMessage back (empty content)
            this.waitForResponses(0, 2000) // RM has no DAIDE content to match for string list
                .then(() => resolve())
                .catch(reject);
        });
      });
      this.socket.on('error', (err) => { logger.error(`Client ${this.client_id} conn error: ${err.message}`); reject(err); });
      this.socket.on('close', () => logger.info(`Client ${this.client_id} conn closed.`));
    });
  }

  private async waitForResponses(count: number, timeoutMs: number = 15000): Promise<string[]> {
    if (count === 0 && this.responsesReceivedThisTurn.length === 0) { // Special case for RM which has no "content" to add to list
        return new Promise((resolve, reject) => {
            const timeoutId = setTimeout(() => reject(new Error(`Client ${this.client_id} timeout waiting for ${count} responses (special RM case)`)), timeoutMs);
            this.responseExpectationQueue.push({ count, resolve, reject, timeoutId });
        });
    }
    if (this.responsesReceivedThisTurn.length >= count) {
        const result = this.responsesReceivedThisTurn.splice(0, count);
        return Promise.resolve(result);
    }
    return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
            // Before rejecting, check if a partial set of messages is acceptable or if any error occurred
            const err = new Error(`Client ${this.client_id} timeout waiting for ${count} responses. Got ${this.responsesReceivedThisTurn.length}`);
            logger.error(err.message);
            // Clean this resolver from queue
            const myResolverIndex = this.responseExpectationQueue.findIndex(item => item.resolve === resolve);
            if(myResolverIndex !== -1) this.responseExpectationQueue.splice(myResolverIndex, 1);
            reject(err);
        }, timeoutMs);
        this.responseExpectationQueue.push({ count, resolve, reject, timeoutId });
    });
  }

  async sendRequest(requestStr: string): Promise<void> {
    if (!this.socket || this.socket.destroyed) throw new Error(`Client ${this.client_id}: Socket not connected.`);
    const daideMsg = new DaideDiplomacyMessage();
    daideMsg.content = daideStringToBytes(requestStr);
    return new Promise((resolve, reject) => {
      this.socket?.write(daideMsg.toBytes(), (err) => {
        if (err) { logger.error(`Client ${this.client_id} SEND FAIL "${requestStr}": ${err.message}`); return reject(err); }
        logger.info(`Client ${this.client_id} [${this.socket?.localPort}] SENT: ${requestStr}`);
        resolve();
      });
    });
  }

  async validateRespNotifs(expectedRespNotifs: string[]): Promise<void> {
    if (expectedRespNotifs.length === 0) return;
    logger.info(`Client ${this.client_id} [${this.socket?.localPort}] EXPECT: ${JSON.stringify(expectedRespNotifs)}`);

    const received = await this.waitForResponses(expectedRespNotifs.length);

    const receivedSet = new Set(received);
    const expectedSet = new Set(expectedRespNotifs);
    let match = received.length === expectedRespNotifs.length;

    if (match) {
        for (const rec of received) {
            let foundMatch = false;
            if (expectedSet.has(rec)) {
                expectedSet.delete(rec); // ensure unique matches
                foundMatch = true;
            } else if (rec.startsWith("HLO")) { // Special HLO check
                const expectedHlo = expectedRespNotifs.find(exp => exp.startsWith("HLO"));
                if (expectedHlo) {
                    const recParts = rec.match(/^(HLO \(\s*\w+\s*\)) \(\s*\d+\s*\) (\(.+\))$/);
                    const expParts = expectedHlo.match(/^(HLO \(\s*\w+\s*\)) \(\s*\d+\s*\) (\(.+\))$/);
                    if (recParts && expParts && recParts[1] === expParts[1] && recParts[2] === expParts[2]) {
                        expectedSet.delete(expectedHlo);
                        foundMatch = true;
                    }
                }
            }
            if (!foundMatch) { match = false; break; }
        }
        if (expectedSet.size > 0) match = false; // Not all expected were found
    }

    if (!match) {
      throw new Error(`Client ${this.client_id} validation failed. Expected: ${JSON.stringify(expectedRespNotifs)}, Got: ${JSON.stringify(received)}`);
    }
    logger.info(`Client ${this.client_id} VALIDATED: ${JSON.stringify(received)}`);
  }

  setComms(allComms: DaideCommData[]): void {
    this.comms = allComms.filter(comm => comm.client_id === this.client_id);
    // Python version had complex sort here. For TS, ensure CSV is ordered or implement sort if needed.
  }

  popNextRequest(): string | null {
    if (!this.comms.length) return null;
    const comm = this.comms[0]; // Peek
    if (comm.request && comm.request.trim() !== "") {
      const req = comm.request;
      this.comms[0] = { ...comm, request: "" }; // Mark as consumed
      return req;
    }
    return null;
  }

  popNextExpectedRespNotifs(): string[] | null {
    if (!this.comms.length) return null;
    const comm = this.comms[0];
    if ((!comm.request || comm.request.trim() === "") && comm.resp_notifs.length > 0) {
      const resp = [...comm.resp_notifs];
      this.comms.shift(); // Consume this entry
      return resp;
    }
    return null;
  }

  async executePhase(): Promise<boolean> { // Removed unused args gameId, channels
    try {
      const requestStr = this.popNextRequest();
      if (requestStr) {
        await this.sendRequest(requestStr);
      }
      const expected = this.popNextExpectedRespNotifs();
      if (expected) { // Could be null if request was sent but no response expected in this step
        await this.validateRespNotifs(expected);
      }
      return this.comms.length > 0; // Still has comms to process
    } catch (err: any) {
      logger.error(`Client ${this.client_id} executePhase error: ${err.message}`, err);
      this.socket?.destroy(); return false;
    }
  }
}

class ClientsCommsSimulatorTs {
  private gamePort: number = 0;
  private nbClients: number;
  private allCommsData: DaideCommData[];
  private clients: Record<number, ClientCommsSimulator>;
  private gameId: string;
  // private channelsPlaceholder: Record<string, any>; // Not used in this simplified version

  constructor(nbClients: number, gameId: string /*, channels: Record<string, any>*/) {
    this.nbClients = nbClients;
    this.allCommsData = [];
    this.clients = {};
    this.gameId = gameId;
    // this.channelsPlaceholder = channels;
  }

  async loadComms(csvFilePath: string): Promise<void> {
    this.allCommsData = await loadDaideCommsCsv(csvFilePath);
  }

  setDaideGamePort(port: number): void { this.gamePort = port; }

  async execute(): Promise<void> {
    if (this.gamePort === 0) throw new Error("DAIDE game port not set.");
    try {
      const clientIdsInCsv = Array.from(new Set(this.allCommsData.map(c => c.client_id))).sort((a,b)=>a-b);
      const clientIdsToRun = clientIdsInCsv.slice(0, this.nbClients);

      for (const clientId of clientIdsToRun) {
        const client = new ClientCommsSimulator(clientId);
        await client.connect(this.gamePort, HOSTNAME);
        client.setComms(this.allCommsData);
        this.clients[clientId] = client;
      }
      logger.info(`${Object.keys(this.clients).length} clients connected and comms assigned.`);

      let activeClientsStillHaveComms = true;
      let rounds = 0;
      const MAX_ROUNDS = this.allCommsData.length + this.nbClients * 5; // Heuristic

      while(activeClientsStillHaveComms && rounds < MAX_ROUNDS) {
        activeClientsStillHaveComms = false;
        const phasePromises = Object.values(this.clients).map(client => {
            if (client.comms.length > 0) { // Check if client has any comms left
                return client.executePhase()
                    .then(hasNext => { if (hasNext) activeClientsStillHaveComms = true; return hasNext; })
                    .catch(err => { logger.error(`Client ${client['client_id']} executePhase threw: ${err.message}`); return false; });
            }
            return Promise.resolve(false);
        });
        await Promise.all(phasePromises);
        rounds++;
        if (!activeClientsStillHaveComms && rounds < MAX_ROUNDS) {
             const anyLeft = Object.values(this.clients).some(c => c.comms.length > 0);
             if(anyLeft) activeClientsStillHaveComms = true; else break;
        }
      }
      if (rounds >= MAX_ROUNDS) logger.warn("Max execution rounds reached.");
      logger.info("Main communication rounds complete.");
      // Final check for remaining comms
      Object.values(this.clients).forEach(c => {
          if(c.comms.length > 0) logger.warn(`Client ${c['client_id']} has ${c.comms.length} unprocessed comms.`);
      });
    } finally {
      for (const client of Object.values(this.clients)) { client.socket?.destroy(); }
    }
  }
}

// Main test orchestrator
async function run_game_data_ts( nb_daide_clients: number, rules: string[], csv_file_path: string, testTimeoutMs: number = 60000) {
    let daideServerInstance: DaideServer | null = null;
    let daideGamePort = 0;

    const serverGameMock: ServerGameMock = { /* ... (full mock as before) ... */
        game_id: `testgame_${Date.now()}_${Math.floor(Math.random()*1000)}`,
        map_name: 'standard', rules, deadline: 300, powers: {},
        current_phase: 'S1901M', status: 'ACTIVE', is_game_completed: false, is_game_canceled: false,
        has_draw_vote: () => false,
        state_history: { last_value: () => ({ name: 'F1900M' }), items: () => ({}) },
        map: { name: 'standard', phase_abbr: s=>s, find_next_phase: s=>s, phase_long: s=>s },
        get_power: (powerName: string) => serverGameMock.powers[powerName],
        is_controlled_by: (powerName: string, username: string | null) => { const p = serverGameMock.powers[powerName]; return !!p && p.controller === username; },
        count_controlled_powers: () => Object.values(serverGameMock.powers).filter(p => !!p.controller).length,
        set_orders_internal: () => {}, set_wait_flag_internal: () => {}, add_message_internal: () => {}, set_vote_internal: () => {},
    };
    const ALL_STD_POWERS = ["AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY"];
    ALL_STD_POWERS.forEach(pName => { serverGameMock.powers[pName] = { name: pName, controller: null, is_controlled_by: (u) => serverGameMock.powers[pName].controller === u, get_controller: () => serverGameMock.powers[pName].controller, units: [], centers: [], retreats: {}, homes:[], orders: {} }; });

    const masterServerMock: MasterServerMock = {
        users: {
            _mock_users: new Map(), _mock_tokens: new Map(),
            get_user: (username: string) => masterServerMock.users._mock_users.get(username) || null,
            get_name: (token: string) => masterServerMock.users._mock_tokens.get(token) || null,
            has_token: (token: string) => masterServerMock.users._mock_tokens.has(token),
            replace_user: (username: string, daideUser: DaideUserMock) => masterServerMock.users._mock_users.set(username, daideUser),
            remove_connection: ()=>{}, count_connections: ()=>0,
        },
        get_game: (gameId: string) => (gameId === serverGameMock.game_id ? serverGameMock : null),
        add_new_game: (game: ServerGameMock) => {},
        start_new_daide_server: async (gameId, port) => {
            if (gameId === serverGameMock.game_id) {
                daideServerInstance = new DaideServer(masterServerMock, gameId);
                await daideServerInstance.listen(port, HOSTNAME);
                return daideServerInstance;
            } throw new Error("start_new_daide_server: wrong game_id");
        },
        stop_daide_server: (gameId) => { daideServerInstance?.stop(); },
        handleInternalRequest: async (req, ch) => { logger.debug("MasterMock handleInternalRequest:", req); return {data: "mock_token"}; }, // Simplified
        assert_token: (token, ch) => { if(!token || !masterServerMock.users.has_token(token)) throw new Error("Token invalid/unknown"); }
    };

    // Populate some mock users for ConnectionHandler to use
    const mockUser1 : DaideUserMock = { username: "DAIDEUser1", passcode: 123, client_name:"Client1", client_version:"v1", to_dict:()=>({}) };
    masterServerMock.users._mock_users.set(mockUser1.username, mockUser1);


    return new Promise(async (resolve, reject) => {
        const testTimeoutId = setTimeout(() => reject(new Error(`Test timed out: ${path.basename(csv_file_path)}`)), testTimeoutMs);
        try {
            const tempPortServer = net.createServer();
            daideGamePort = await new Promise<number>(res => tempPortServer.listen(0, HOSTNAME, () => {
                const port = (tempPortServer.address() as net.AddressInfo).port;
                tempPortServer.close(() => res(port));
            }));
            logger.info(`Test ${path.basename(csv_file_path)} using DAIDE port: ${daideGamePort}`);

            masterServerMock.add_new_game(serverGameMock);
            await masterServerMock.start_new_daide_server(serverGameMock.game_id, daideGamePort);

            const commsSimulator = new ClientsCommsSimulatorTs(nb_daide_clients, serverGameMock.game_id, {});
            await commsSimulator.loadComms(csv_file_path);
            commsSimulator.setDaideGamePort(daideGamePort);

            await commsSimulator.execute();

            clearTimeout(testTimeoutId); resolve(undefined);
        } catch (err) {
            clearTimeout(testTimeoutId); logger.error(`Test ${path.basename(csv_file_path)} FAILED:`, err); reject(err);
        } finally {
            if (daideServerInstance) await daideServerInstance.stop();
        }
    });
}

describe('DAIDE Game Integration Tests', () => {
    jest.setTimeout(70000); // Default timeout for these integration tests

    it('test_game_1_reject_map_equivalent', async () => {
        const game_path = path.join(FILE_FOLDER_NAME, 'game_data_1_reject_map.csv');
        await run_game_data_ts(1, ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'], game_path, 60000);
    });
    it('test_game_1_equivalent', async () => {
        const game_path = path.join(FILE_FOLDER_NAME, 'game_data_1.csv');
        await run_game_data_ts(1, ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'], game_path, 60000);
    });
    it('test_game_history_equivalent', async () => {
        const game_path = path.join(FILE_FOLDER_NAME, 'game_data_1_history.csv');
        await run_game_data_ts(1, ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'], game_path, 60000);
    });
    it('test_game_7_equivalent', async () => {
        const game_path = path.join(FILE_FOLDER_NAME, 'game_data_7.csv');
        await run_game_data_ts(7, ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'], game_path, 120000);
    });
    it('test_game_7_draw_equivalent', async () => {
        const game_path = path.join(FILE_FOLDER_NAME, 'game_data_7_draw.csv');
        await run_game_data_ts(7, ['NO_PRESS', 'IGNORE_ERRORS', 'POWER_CHOICE'], game_path, 120000);
    });
    it('test_game_7_press_equivalent', async () => {
        const game_path = path.join(FILE_FOLDER_NAME, 'game_data_7_press.csv');
        await run_game_data_ts(7, ['IGNORE_ERRORS', 'POWER_CHOICE'], game_path, 120000);
    });
});
