// diplomacy/daide/connection_handler.ts

import * as net from 'net';
import { Buffer } from 'buffer';
import { DaideServer } from './server'; // Assuming server.ts exports DaideServer
import {
    DaideMessage, MessageType, ErrorCode,
    InitialMessage, RepresentationMessage, DiplomacyMessage as DaideDiplomacyMessage, // Renamed to avoid conflict
    FinalMessage, ErrorMessage as DaideErrorMessage
} from './messages'; // Assuming messages.ts is available
import { bytes_to_str as daideBytesToString } from './utils'; // Assuming utils.ts is available

// Placeholders for DAIDE-specific request/response/notification handling logic
// These would be imported from ./request_managers, ./notification_managers, etc.
interface DaideRequest { /* ... */ } // Placeholder
interface DaideResponse { /* ... */ toBytes(): Buffer; } // Placeholder, needs toBytes
interface DaideNotification { /* ... */ toBytes(): Buffer; } // Placeholder, needs toBytes

const RequestBuilder = { // Placeholder
  from_bytes: (content: Buffer): DaideRequest | null => {
    logger.warn(`RequestBuilder.from_bytes called with content length ${content.length}. Placeholder.`);
    return null; // Or a mock request
  }
};
const DaideRequestManagers = { // Placeholder
  handle_request: async (server: any, request: DaideRequest, handler: ConnectionHandlerTs): Promise<DaideResponse[] | null> => {
    logger.warn(`DaideRequestManagers.handle_request called. Placeholder.`);
    return null; // Or mock responses
  }
};
const DaideNotificationManagers = { // Placeholder
    translate_notification: (server: any, general_notification: any, handler: ConnectionHandlerTs): DaideNotification[] | null => {
        logger.warn(`DaideNotificationManagers.translate_notification called. Placeholder.`);
        return null;
    }
};
const DaideResponses = { // Placeholder for specific DAIDE response constructors if needed (e.g. REJ)
    REJ: (content: Buffer): DaideResponse => {
        logger.warn(`DaideResponses.REJ called. Placeholder.`);
        // This should construct a proper REJ response in DAIDE bytes
        return { toBytes: () => Buffer.from("REJ_PLACEHOLDER_BYTES") };
    }
};


// Logger
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// Helper class to read from a buffer sequentially, similar to one in messages.ts
class BufferReader {
    private buffer: Buffer;
    private offset: number = 0;

    constructor(buffer: Buffer) {
        this.buffer = buffer;
    }
    readBytes(length: number): Buffer {
        if (this.offset + length > this.buffer.length) {
            throw new Error("BufferReader: Not enough bytes to read.");
        }
        const slice = this.buffer.slice(this.offset, this.offset + length);
        this.offset += length;
        return slice;
    }
    get remainingBuffer(): Buffer {
        return this.buffer.slice(this.offset);
    }
    get remainingLength(): number { return this.buffer.length - this.offset; }
    isExhausted(): boolean { return this.offset >= this.buffer.length; }
    prepend(data: Buffer): void {
        this.buffer = Buffer.concat([data, this.buffer.slice(this.offset)]);
        this.offset = 0;
    }
}


export class ConnectionHandlerTs {
  private socket: net.Socket;
  private daideServer: DaideServer; // Reference to the parent DAIDE server instance
  private gameId: string;
  public token: string | null = null; // DAIDE token, set after successful IAM or similar
  private nameVariant: string | null = null;
  private dataBuffer: Buffer = Buffer.alloc(0);

  // For name variants, similar to Python static members
  private static _NAME_VARIANT_PREFIX = 'DAIDE';
  private static _NAME_VARIANTS_POOL: number[] = [];
  private static _USED_NAME_VARIANTS: number[] = [];


  constructor(socket: net.Socket, daideServer: DaideServer, gameId: string) {
    this.socket = socket;
    this.daideServer = daideServer;
    this.gameId = gameId;

    // Note: In Python, initialize was separate. Here, constructor handles it.
    // this.stream.set_close_callback equivalent is socket.on('close', ...) handled by DaideServer
    // this._socket_no = this.socket. Kinda like a unique ID for the socket if needed.
    // this._local_addr and this._remote_addr are available on socket.localAddress/Port, socket.remoteAddress/Port
  }

  public startProcessing(): void {
    this.socket.on('data', (dataChunk: Buffer) => {
      this._handleData(dataChunk);
    });
  }

  private async _handleData(dataChunk: Buffer): Promise<void> {
    this.dataBuffer = Buffer.concat([this.dataBuffer, dataChunk]);

    while (this.dataBuffer.length >= 4) { // Minimum length for a DAIDE header
      const messageTypeVal = this.dataBuffer.readUInt8(0);
      // const padding = this.dataBuffer.readUInt8(1);
      const remainingLength = this.dataBuffer.readUInt16BE(2);
      const totalMessageLength = 4 + remainingLength;

      if (this.dataBuffer.length >= totalMessageLength) {
        const messageBuffer = this.dataBuffer.slice(0, totalMessageLength);
        this.dataBuffer = this.dataBuffer.slice(totalMessageLength);

        const messageReader = new BufferReader(messageBuffer);
        try {
          // DaideMessage.fromBuffer expects the reader to be positioned at the start of the *payload*
          // after it reads the header itself. Let's adjust.
          // Header is 4 bytes. fromBuffer reads it. Payload follows.
          // So, pass the reader for the whole message.
          const daideMessage = await DaideMessage.fromBuffer(messageReader); // fromBuffer now handles header itself
          await this.processDaideMessage(daideMessage);
        } catch (e: any) {
          logger.error(`Error parsing DAIDE message: ${e.message}`, e);
          // Potentially send an error message back or close connection
          const errMsg = new DaideErrorMessage(ErrorCode.UNKNOWN_MESSAGE); // Or more specific
          await this.writeMessage(errMsg);
          this.socket.end(); // Close connection on parsing error
          break;
        }
      } else {
        break; // Not enough data for the full message, wait for more
      }
    }
  }

  private async processDaideMessage(message: DaideMessage): Promise<void> {
    let responsesToSend: DaideMessage[] = [];
    if (message.isValid) {
      const handler = this.getMessageHandler(message.messageType);
      if (!handler) {
        logger.error(`Unrecognized DAIDE message type: ${message.messageType}`);
        const errMsg = new DaideErrorMessage(ErrorCode.UNKNOWN_MESSAGE);
        responsesToSend.push(errMsg);
      } else {
        try {
          const handlerResponses = await handler(message);
          if (handlerResponses) {
            responsesToSend.push(...handlerResponses);
          }
        } catch (e: any) {
            logger.error(`Error in message handler for type ${message.messageType}: ${e.message}`, e);
            const errMsg = new DaideErrorMessage(ErrorCode.UNKNOWN_MESSAGE); // Or a more generic server error
            responsesToSend.push(errMsg);
        }
      }
    } else {
      logger.warn(`Received invalid DAIDE message. Error code: ${message.errorCode}`);
      const errMsg = new DaideErrorMessage(message.errorCode || ErrorCode.UNKNOWN_MESSAGE);
      responsesToSend.push(errMsg);
    }

    for (const رسالة of responsesToSend) {
      await this.writeMessage(رسالة);
    }
  }

  private getMessageHandler(messageType: MessageType): ((msg: DaideMessage) => Promise<DaideMessage[] | null>) | null {
    switch (messageType) {
      case MessageType.INITIAL: return this._onInitialMessage.bind(this);
      case MessageType.DIPLOMACY: return this._onDiplomacyMessage.bind(this);
      case MessageType.FINAL: return this._onFinalMessage.bind(this);
      case MessageType.ERROR: return this._onErrorMessage.bind(this);
      default: return null;
    }
  }

  public getNameVariant(): string {
    if (this.nameVariant === null) {
      const pool = ConnectionHandlerTs._NAME_VARIANTS_POOL;
      const used = ConnectionHandlerTs._USED_NAME_VARIANTS;
      this.nameVariant = pool.length > 0 ? String(pool.pop()) : String(used.length);
      used.push(parseInt(this.nameVariant, 10)); // Assuming variant is stored as number in pool
    }
    return ConnectionHandlerTs._NAME_VARIANT_PREFIX + this.nameVariant;
  }

  public releaseNameVariant(): void {
    if (this.nameVariant !== null) {
      const used = ConnectionHandlerTs._USED_NAME_VARIANTS;
      const idx = used.indexOf(parseInt(this.nameVariant, 10));
      if (idx > -1) used.splice(idx, 1);
      ConnectionHandlerTs._NAME_VARIANTS_POOL.push(parseInt(this.nameVariant, 10));
      this.nameVariant = null;
    }
  }

  public async closeConnection(): Promise<void> {
    try {
      // Constructing a TurnOffResponse equivalent.
      // This response type isn't explicitly defined in messages.py but is implied by OFF token.
      // For now, sending a generic FinalMessage or a specific "TurnOff" message if defined.
      // Python code: message.content = bytes(responses.TurnOffResponse()) -> results in DiplomacyMessage.
      // Let's assume TurnOff is a type of DiplomacyMessage content.
      // For now, let's send a FinalMessage as a signal to close.
      const finalMsg = new FinalMessage();
      await this.writeMessage(finalMsg);
    } catch (e: any) {
      logger.error(`Error sending final message during closeConnection: ${e.message}`);
    } finally {
      this.socket.end(); // Gracefully close
      this.socket.destroy(); // Ensure full closure
    }
  }

  public onClose(): void {
    this.releaseNameVariant();
    // Notify master server to remove connection from its user tracking
    // this.daideServer.MasterServer.users.remove_connection(this, remove_tokens=False); // Placeholder
    logger.info(`Connection handler for ${this.socket.remoteAddress}:${this.socket.remotePort} cleaned up.`);
    // Further cleanup if necessary
  }

  public writeMessage(message: DaideMessage | Buffer, binary: boolean = true): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.socket.destroyed || !this.socket.writable) {
        logger.error("Attempted to write to a closed or non-writable socket.");
        return reject(new Error("Socket not writable."));
      }

      let bufferToWrite: Buffer;
      if (message instanceof Buffer) {
        bufferToWrite = message;
      } else if (message instanceof DaideMessage) {
        bufferToWrite = message.toBytes();
      } else {
        logger.error("Invalid message type for writeMessage:", message);
        return reject(new Error("Invalid message type for writeMessage"));
      }

      // Logging DAIDE messages (similar to Python version)
      if (message instanceof DaideMessage && message.messageType === MessageType.DIPLOMACY) {
          logger.info(`[Socket ${this.socket.remotePort}] SEND DAIDE Diplomacy: ${daideBytesToString(message.content)}`);
      } else if (message instanceof DaideMessage) {
          logger.info(`[Socket ${this.socket.remotePort}] SEND DAIDE System: ${MessageType[message.messageType]}`);
      }


      this.socket.write(bufferToWrite, (err) => {
        if (err) {
          logger.error(`Error writing to socket: ${err.message}`, err);
          reject(err);
        } else {
          resolve();
        }
      });
    });
  }

  // Placeholder for the DAIDE-specific translate_notification
  public translateDaideNotification(general_notification: any): DaideNotification[] | null {
    // return DaideNotificationManagers.translate_notification(this.daideServer.MasterServer, general_notification, this);
    logger.warn("translateDaideNotification placeholder called.");
    return null;
  }

  // Message Handlers
  private async _onInitialMessage(message: InitialMessage): Promise<DaideMessage[] | null> {
    logger.info(`[Socket ${this.socket.remotePort}] initial message received.`);
    // Validation of InitialMessage (version, magic number) happens in its build method.
    // If it's invalid, message.isValid would be false and message.errorCode set.
    // The processDaideMessage method already handles sending an ErrorMessage if !isValid.
    if (!message.isValid) return null; // Error already sent by processDaideMessage
    return [new RepresentationMessage()];
  }

  private async _onDiplomacyMessage(message: DaideDiplomacyMessage): Promise<DaideMessage[] | null> {
    logger.info(`[Socket ${this.socket.remotePort}] RECV DAIDE Diplomacy: ${daideBytesToString(message.content)}`);
    const responsesToSend: DaideMessage[] = [];
    const request = RequestBuilder.from_bytes(message.content); // This is a DAIDE request

    if (!request) {
        logger.error(`[Socket ${this.socket.remotePort}] Failed to parse DAIDE request from diplomacy message content.`);
        responsesToSend.push(new DaideErrorMessage(ErrorCode.UNKNOWN_MESSAGE)); // Or more specific
        return responsesToSend;
    }

    try {
      // Assuming request object gets game_id property set by RequestBuilder or needs it set here
      (request as any).game_id = this.gameId; // Ensure request has game_id for handler

      const daideResponses = await DaideRequestManagers.handle_request(this.daideServer.MasterServer, request, this);

      if (daideResponses) {
        for (const daideResponse of daideResponses) {
          const diplomacyMsg = new DaideDiplomacyMessage();
          diplomacyMsg.content = daideResponse.toBytes(); // Each DAIDE response needs a toBytes method
          responsesToSend.push(diplomacyMsg);
        }
      }
    } catch (e: any) {
      logger.error(`[Socket ${this.socket.remotePort}] Error handling DAIDE request: ${e.message}`, e);
      // Convert exception to a DAIDE REJ response or specific error
      const rejResponse = DaideResponses.REJ(message.content); // Assuming REJ takes original request bytes
      const diplomacyMsg = new DaideDiplomacyMessage();
      diplomacyMsg.content = rejResponse.toBytes();
      responsesToSend.push(diplomacyMsg);
    }
    return responsesToSend;
  }

  private async _onFinalMessage(message: FinalMessage): Promise<DaideMessage[] | null> {
    logger.info(`[Socket ${this.socket.remotePort}] final message received. Closing connection.`);
    this.socket.end(); // Close the socket
    return []; // No response to send
  }

  private async _onErrorMessage(message: DaideErrorMessage): Promise<DaideMessage[] | null> {
    logger.error(`[Socket ${this.socket.remotePort}] error message received from client: Code ${message.errorCode}`);
    // Typically, server doesn't respond to an error message from client, just logs it.
    return [];
  }
}
