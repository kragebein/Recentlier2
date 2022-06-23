#!/usr/bin/python3.10
import asyncio
from recentlier.main import Recentlier

if __name__ == '__main__':

    sp = Recentlier()
    asyncio.run(sp.run())
