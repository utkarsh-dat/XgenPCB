// Command Engine: Implements Undo/Redo, history tracking, keybindings, and action orchestration
export interface Command {
  execute(): void;
  undo(): void;
}

export class CommandEngine {
  private history: Command[] = [];
  private redoStack: Command[] = [];

  execute(command: Command) {
    command.execute();
    this.history.push(command);
    this.redoStack = []; // Clear redo stack on new action
  }

  undo() {
    const command = this.history.pop();
    if (command) {
      command.undo();
      this.redoStack.push(command);
    }
  }

  redo() {
    const command = this.redoStack.pop();
    if (command) {
      command.execute();
      this.history.push(command);
    }
  }

  registerKeybindings() {
    window.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'z') {
        this.undo();
      } else if (e.ctrlKey && e.key === 'y') {
        this.redo();
      }
    });
  }
}

export const commandEngine = new CommandEngine();
