// diplomacy/daide/messages.ts

import { Buffer } from 'buffer'; // Node.js Buffer

// Logger
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// Constants
const DAIDE_VERSION = 1;

export enum MessageType {
  INITIAL = 0,
  REPRESENTATION = 1,
  DIPLOMACY = 2,
  FINAL = 3,
  ERROR = 4,
}

export enum ErrorCode {
  IM_TIMER_POPPED = 0x01,
  IM_NOT_FIRST_MESSAGE = 0x02,
  IM_WRONG_ENDIAN = 0x03,
  IM_WRONG_MAGIC_NUMBER = 0x04,
  VERSION_INCOMPATIBILITY = 0x05,
  MORE_THAN_1_IM_SENT = 0x06,
  IM_SENT_BY_SERVER = 0x07,
  UNKNOWN_MESSAGE = 0x08,
  MESSAGE_SHORTER_THAN_EXPECTED = 0x09,
  DM_SENT_BEFORE_RM = 0x0A,
  RM_NOT_FIRST_MSG_BY_SERVER = 0x0B,
  MORE_THAN_1_RM_SENT = 0x0C,
  RM_SENT_BY_CLIENT = 0x0D,
  INVALID_TOKEN_DM = 0x0E,
}

/**
 * Helper class to read from a buffer sequentially.
 */
class BufferReader {
    private buffer: Buffer;
    private offset: number = 0;

    constructor(buffer: Buffer) {
        this.buffer = buffer;
    }

    readBytes(length: number): Buffer {
        if (this.offset + length > this.buffer.length) {
            throw new Error("Not enough bytes in buffer to read.");
        }
        const slice = this.buffer.slice(this.offset, this.offset + length);
        this.offset += length;
        return slice;
    }

    get remainingLength(): number {
        return this.buffer.length - this.offset;
    }

    isExhausted(): boolean {
        return this.offset >= this.buffer.length;
    }
}


export abstract class DaideMessage {
  messageType: MessageType;
  isValid: boolean = true;
  errorCode: ErrorCode | null = null;
  content: Buffer = Buffer.alloc(0); // Use Node.js Buffer for byte content

  constructor(messageType: MessageType) {
    this.messageType = messageType;
  }

  abstract toBytes(): Buffer;
  abstract build(payloadReader: BufferReader, declaredLength: number): Promise<void>;

  /**
   * Creates a DaideMessage from a Buffer representing the start of a stream.
   * The `streamReader` is a function that can be called to asynchronously fetch more bytes if needed.
   * For simpler protocols or testing, the initialBuffer might contain the whole message.
   */
  static async fromBuffer(
    initialBufferReader: BufferReader,
    streamReader?: (length: number) => Promise<Buffer> // Optional: For fetching more data if needed
  ): Promise<DaideMessage> {
    if (initialBufferReader.remainingLength < 4) {
        throw new Error('Initial buffer too short for DAIDE message header.');
    }
    const header = initialBufferReader.readBytes(4); // Message type, Pad, Remaining Length (2x)
    const messageTypeValue = header.readUInt8(0);
    // const padding = header.readUInt8(1); // Padding is byte 1
    const remainingLength = header.readUInt16BE(2); // Bytes 2 and 3 for length

    let MessageClass: (new () => DaideMessage) | undefined;
    switch (messageTypeValue) {
      case MessageType.INITIAL: MessageClass = InitialMessage; break;
      case MessageType.REPRESENTATION: MessageClass = RepresentationMessage; break;
      case MessageType.DIPLOMACY: MessageClass = DiplomacyMessage; break;
      case MessageType.FINAL: MessageClass = FinalMessage; break;
      case MessageType.ERROR: MessageClass = ErrorMessage; break;
      default:
        throw new Error(`Unknown Message Type ${messageTypeValue}`);
    }

    const message = new MessageClass();

    // The payload is 'remainingLength' bytes.
    // We need to ensure we have enough bytes for the payload.
    let payloadBuffer: Buffer;
    if (initialBufferReader.remainingLength >= remainingLength) {
        payloadBuffer = initialBufferReader.readBytes(remainingLength);
    } else if (streamReader) {
        const neededFromStream = remainingLength - initialBufferReader.remainingLength;
        const streamData = await streamReader(neededFromStream);
        payloadBuffer = Buffer.concat([initialBufferReader.readBytes(initialBufferReader.remainingLength), streamData]);
        if (payloadBuffer.length < remainingLength) {
            throw new Error(`Stream did not provide enough bytes for payload. Expected ${remainingLength}, got ${payloadBuffer.length}`);
        }
    } else {
        throw new Error(`Not enough bytes in initial buffer for payload (${initialBufferReader.remainingLength}/${remainingLength}) and no streamReader provided.`);
    }

    const payloadReader = new BufferReader(payloadBuffer);
    await message.build(payloadReader, remainingLength);
    return message;
  }
}

export class InitialMessage extends DaideMessage {
  constructor() {
    super(MessageType.INITIAL);
  }

  toBytes(): Buffer {
    const buffer = Buffer.alloc(8);
    buffer.writeUInt8(this.messageType, 0);
    buffer.writeUInt8(0, 1); // Padding
    buffer.writeUInt16BE(4, 2); // Remaining length
    buffer.writeUInt16BE(DAIDE_VERSION, 4); // DAIDE version
    buffer.writeUInt16BE(0xDA10, 6); // Magic Number
    return buffer;
  }

  async build(payloadReader: BufferReader, declaredLength: number): Promise<void> {
    if (declaredLength !== 4) {
      logger.error(`Expected 4 bytes remaining in initial message. Got ${declaredLength}.`);
      this.isValid = false;
      // Consume declared bytes if any to clear the stream for next message
      if (declaredLength > 0 && payloadReader.remainingLength >= declaredLength) {
          payloadReader.readBytes(declaredLength);
      }
      return;
    }
    if (payloadReader.remainingLength < 4) {
        this.isValid = false;
        this.errorCode = ErrorCode.MESSAGE_SHORTER_THAN_EXPECTED; // Or a more specific error
        logger.error('InitialMessage: Payload too short.');
        return;
    }

    const version = payloadReader.readBytes(2).readUInt16BE(0);
    const magicNumber = payloadReader.readBytes(2).readUInt16BE(0);

    if (version !== DAIDE_VERSION) {
      this.isValid = false;
      this.errorCode = ErrorCode.VERSION_INCOMPATIBILITY;
      logger.error(`Client sent version ${version}. Server version is ${DAIDE_VERSION}`);
      return;
    }

    if (magicNumber === 0x10DA) { // Endian issue
      this.isValid = false;
      this.errorCode = ErrorCode.IM_WRONG_ENDIAN;
    } else if (magic_number !== 0xDA10) {
      this.isValid = false;
      this.errorCode = ErrorCode.IM_WRONG_MAGIC_NUMBER;
    }
  }
}

export class RepresentationMessage extends DaideMessage {
  constructor() {
    super(MessageType.REPRESENTATION);
  }

  toBytes(): Buffer {
    const buffer = Buffer.alloc(4);
    buffer.writeUInt8(this.messageType, 0);
    buffer.writeUInt8(0, 1); // Padding
    buffer.writeUInt16BE(0, 2); // Remaining length
    return buffer;
  }

  async build(payloadReader: BufferReader, declaredLength: number): Promise<void> {
    if (declaredLength > 0) {
        if (payloadReader.remainingLength < declaredLength) {
             logger.error(`RepresentationMessage: Declared length ${declaredLength} but not enough bytes in payload.`);
             this.isValid = false; return;
        }
        payloadReader.readBytes(declaredLength); // Consume if any, though spec says length 0
    }
    // Python code sets isValid = False and error_code = RM_SENT_BY_CLIENT.
    // This implies that if a server *receives* this, it's an error.
    // For parsing logic, we assume it's valid if structure matches.
    // The error RM_SENT_BY_CLIENT would be set by the server if it received this from a client.
    // If we are a client parsing this from a server, it should be valid.
    // For now, let's keep it simple. If the server sends it, it's valid.
    // The Python server code would raise an error if it *receives* an RM from a client.
    // Here, we are defining the message structure and how to parse it if *we* receive it.
  }
}

export class DiplomacyMessage extends DaideMessage {
  constructor() {
    super(MessageType.DIPLOMACY);
  }

  toBytes(): Buffer {
    if (!this.isValid) {
      return Buffer.alloc(0); // Or throw error
    }
    const header = Buffer.alloc(4);
    header.writeUInt8(this.messageType, 0);
    header.writeUInt8(0, 1); // Padding
    header.writeUInt16BE(this.content.length, 2); // Remaining length is content length
    return Buffer.concat([header, this.content]);
  }

  async build(payloadReader: BufferReader, declaredLength: number): Promise<void> {
    if (declaredLength < 0 || declaredLength % 2 !== 0) { // DAIDE content is pairs of bytes
      this.isValid = false;
      if (declaredLength > 0 && payloadReader.remainingLength >= declaredLength) {
          payloadReader.readBytes(declaredLength); // Consume to clear
      }
      logger.warn(`DiplomacyMessage: Invalid length ${declaredLength}. Must be even and non-negative.`);
      this.errorCode = ErrorCode.MESSAGE_SHORTER_THAN_EXPECTED; // Or a more specific error
      return;
    }
    if (payloadReader.remainingLength < declaredLength) {
        this.isValid = false;
        this.errorCode = ErrorCode.MESSAGE_SHORTER_THAN_EXPECTED;
        logger.error(`DiplomacyMessage: Declared length ${declaredLength} but not enough bytes in payload.`);
        return;
    }
    this.content = payloadReader.readBytes(declaredLength);
  }
}

export class FinalMessage extends DaideMessage {
  constructor() {
    super(MessageType.FINAL);
  }
  toBytes(): Buffer {
    const buffer = Buffer.alloc(4);
    buffer.writeUInt8(this.messageType, 0);
    buffer.writeUInt8(0, 1); // Padding
    buffer.writeUInt16BE(0, 2); // Remaining length
    return buffer;
  }
  async build(payloadReader: BufferReader, declaredLength: number): Promise<void> {
    if (declaredLength > 0) {
        if (payloadReader.remainingLength < declaredLength) {
            logger.error(`FinalMessage: Declared length ${declaredLength} but not enough bytes.`);
            this.isValid = false; return;
        }
      payloadReader.readBytes(declaredLength); // Consume if any
    }
  }
}

export class ErrorMessage extends DaideMessage {
  constructor(code?: ErrorCode) { // Allow constructing with an error code
    super(MessageType.ERROR);
    if (code) {
        this.errorCode = code;
    }
  }
  toBytes(): Buffer {
    const buffer = Buffer.alloc(6);
    buffer.writeUInt8(this.messageType, 0);
    buffer.writeUInt8(0, 1); // Padding
    buffer.writeUInt16BE(2, 2); // Remaining length (2 bytes for error code)
    buffer.writeUInt16BE(this.errorCode !== null ? this.errorCode.valueOf() : 0, 4); // Error code
    return buffer;
  }
  async build(payloadReader: BufferReader, declaredLength: number): Promise<void> {
    if (declaredLength !== 2) {
      this.isValid = false;
      if (declaredLength > 0 && payloadReader.remainingLength >= declaredLength) {
          payloadReader.readBytes(declaredLength);
      }
      logger.error(`ErrorMessage: Expected 2 bytes for payload, got ${declaredLength}.`);
      // this.errorCode could be set to a generic parsing error if desired
      return;
    }
     if (payloadReader.remainingLength < 2) {
        this.isValid = false;
        this.errorCode = ErrorCode.MESSAGE_SHORTER_THAN_EXPECTED; // Generic, or specific to error msg format
        logger.error('ErrorMessage: Payload too short for error code.');
        return;
    }
    const errorCodeValue = payloadReader.readBytes(2).readUInt16BE(0);
    if (ErrorCode[errorCodeValue] !== undefined) {
      this.errorCode = errorCodeValue as ErrorCode;
    } else {
      logger.warn(`Unknown error code received: ${errorCodeValue}`);
      this.isValid = false; // Or handle as a generic error
    }
  }
}
