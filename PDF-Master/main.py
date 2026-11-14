"""PDF Master entry point."""


def main() -> None:
    try:
        from app.application import run
    except ImportError:
        print("PDF Master's user interface has not been built yet.")
        print("The PDF engine is ready: run run_tests.bat (or 'python -m pytest') to verify it.")
        raise SystemExit(0)
    run()


if __name__ == "__main__":
    main()
