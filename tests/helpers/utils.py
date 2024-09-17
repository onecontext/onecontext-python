import time

from onecontext.context import Context


def wait_for_file_processing(context: Context, timeout_seconds: int = 180):
    start_time = time.time()

    while True:
        files = context.list_files()
        if all(file.status == "COMPLETED" for file in files):
            break
        if any(file.status == "FAILED" for file in files):
            print(files)
            raise RuntimeError("One or more files have failed to process.")
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError(f"Upload timed out after {timeout_seconds} seconds.")
        time.sleep(10)
