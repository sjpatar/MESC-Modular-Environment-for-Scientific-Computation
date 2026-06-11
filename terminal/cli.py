import sys
import argparse
from ides.mathex.kernel.session import KernelSession
from ides.mathex.kernel.executor import execute

def main():
    parser = argparse.ArgumentParser(description="Mathex CLI")
    parser.add_argument('file', nargs='?', help="Script file to run")
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Disable filesystem and Python escape hatches for web-facing execution.",
    )
    args = parser.parse_args()

    session = KernelSession(safe_mode=args.safe_mode)

    if args.file:
        try:
            with open(args.file, 'r') as f:
                code = f.read()
            # Execute file content
            execute(code, session)
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        # Start REPL
        print("Mathex CLI 1.0. Type 'exit' to quit.")
        while True:
            try:
                line = input(">> ")
                if line.strip() == 'exit': break
                res = execute(line, session)
                if res: print(res)
            except KeyboardInterrupt:
                print("\n")
                break

if __name__ == "__main__":
    main()
