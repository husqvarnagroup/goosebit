#!/usr/bin/env python3

from time import sleep

VERSION = "0.1.0"

def main():
    while True:
        print(f"Hello from version {VERSION}!", flush=True)
        sleep(5)


if __name__ == "__main__":
    main()
