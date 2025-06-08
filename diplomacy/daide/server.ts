// diplomacy/daide/server.ts

import * as net from 'net';
import { ConnectionHandlerTs } from './connection_handler'; // To be created

// Logger
const logger = {
  debug: (message: string) => console.debug(message),
  info: (message: string) => console.info(message),
  warn: (message: string) => console.warn(message),
  error: (message: string, error?: any) => console.error(message, error),
};

// Placeholder for the MasterServer type/interface
interface MasterServer {
  // Define methods/properties of master_server that ConnectionHandler might use
  // For example, getting game data, authenticating users, etc.
  getGameById(gameId: string): any; // Example
  // ... other master server functionalities
}

export class DaideServer {
  private masterServer: MasterServer;
  private gameId: string;
  private nodeServer: net.Server;
  private registeredConnections: Map<net.Socket, ConnectionHandlerTs>;

  constructor(masterServer: MasterServer, gameId: string) {
    this.masterServer = masterServer;
    this.gameId = gameId;
    this.registeredConnections = new Map<net.Socket, ConnectionHandlerTs>();

    this.nodeServer = net.createServer((socket: net.Socket) => {
      this.handleConnection(socket);
    });

    this.nodeServer.on('error', (err: Error) => {
      logger.error(`DAIDE Server error: ${err.message}`, err);
    });

    this.nodeServer.on('close', () => {
      logger.info(`DAIDE Server for game ${this.gameId} has closed.`);
    });
  }

  get MasterServer(): MasterServer {
    return this.masterServer;
  }

  get GameId(): string {
    return this.gameId;
  }

  private handleConnection(socket: net.Socket): void {
    const address = `${socket.remoteAddress}:${socket.remotePort}`;
    logger.info(`DAIDE client connected from [${address}] for game ${this.gameId}`);

    // The ConnectionHandler will manage reading DAIDE messages from this socket
    const handler = new ConnectionHandlerTs(socket, this.masterServer, this.gameId);
    this.registeredConnections.set(socket, handler);

    // The ConnectionHandler's internal logic (e.g., on 'data' event) will replace
    // the `yield handler.read_stream()` loop from the Python version.
    // It should start its own processing of incoming data.
    handler.startProcessing(); // Assume ConnectionHandlerTs has a method to begin its work

    socket.on('close', (hadError: boolean) => {
      logger.info(`DAIDE client [${address}] disconnected ${hadError ? 'due to an error' : 'gracefully'}.`);
      this.registeredConnections.delete(socket);
      handler.onClose(); // Notify handler to clean up if necessary
    });

    socket.on('error', (err: Error) => {
      logger.error(`DAIDE client [${address}] socket error: ${err.message}`, err);
      // Close event will follow, which handles cleanup.
      // Optionally, handler.onError(err) if specific error handling in handler is needed.
    });
  }

  public listen(port: number, hostname?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.nodeServer.listen(port, hostname, () => {
        const address = this.nodeServer.address();
        const addrStr = typeof address === 'string' ? address : `${address?.address}:${address?.port}`;
        logger.info(`DAIDE Server for game ${this.gameId} listening on ${addrStr}`);
        resolve();
      });
      this.nodeServer.once('error', (err) => { // Handle listen errors e.g. EADDRINUSE
          reject(err);
      });
    });
  }

  public stop(): Promise<void> {
    return new Promise((resolve, reject) => {
      logger.info(`Stopping DAIDE Server for game ${this.gameId}...`);
      this.registeredConnections.forEach((handler, socket) => {
        try {
          // handler.closeConnection(); // Python version had this, ConnectionHandlerTs should handle socket.end() or destroy()
          socket.end(); // Gracefully end client connections
          socket.destroy(); // Ensure socket is destroyed
        } catch (e: any) {
            logger.error(`Error closing client socket: ${e.message}`);
        }
      });
      this.registeredConnections.clear();

      this.nodeServer.close((err?: Error) => {
        if (err) {
          logger.error(`Error stopping DAIDE server: ${err.message}`, err);
          reject(err);
        } else {
          logger.info(`DAIDE Server for game ${this.gameId} stopped successfully.`);
          resolve();
        }
      });
    });
  }
}

// Example usage (conceptual):
// const masterServerInstance = /* ... your master server logic ... */;
// const daideServer = new DaideServer(masterServerInstance, "some_game_id");
// daideServer.listen(16713, "localhost")
//   .then(() => console.log("DAIDE server running."))
//   .catch(err => console.error("Failed to start DAIDE server:", err));
