"""Compatibility import; the 11.2.4 node now lives in sensors/imu_processor.py."""
from my_quadruped_bot.sensors.imu_processor import ImuProcessor, main

__all__ = ['ImuProcessor', 'main']

if __name__ == '__main__':
    main()
