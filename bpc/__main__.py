import click


@click.command()
@click.version_option(version="0.1.0", prog_name="bpc")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
def main(verbose: bool):
    pass


if __name__ == "__main__":
    main()  # type: ignore[call-arg]
