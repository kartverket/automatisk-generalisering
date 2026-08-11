from io_adapters import make_local_fs_read_write
from run_partition import run_partition_worker


def main() -> None:
    read, write = make_local_fs_read_write(adapter_name="on_prem")
    run_partition_worker(read=read, write=write)


if __name__ == "__main__":
    main()
