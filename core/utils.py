import random
import time
import math

class HumanBehavior:
    @staticmethod
    def sleep_random(min_seconds=2, max_seconds=10):
        """Sleep for a random amount of time to simulate human thinking/reading."""
        sleep_time = random.uniform(min_seconds, max_seconds)
        time.sleep(sleep_time)
        return sleep_time

    @staticmethod
    def calculate_mouse_movement(start_x, start_y, end_x, end_y):
        """
        Simulate a human-like mouse movement path (Bezier curve).
        Returns a list of (x, y) coordinates.
        This is a simplified version, Playwright handles some of this, 
        but we can use this for explicit 'mouse moving' logic if needed.
        """
        path = []
        steps = random.randint(10, 50)
        for i in range(steps):
             t = i / steps
             # Linear interpolation for now, can be upgraded to Bezier
             x = start_x + (end_x - start_x) * t
             y = start_y + (end_y - start_y) * t
             # Add some jitter
             x += random.uniform(-2, 2)
             y += random.uniform(-2, 2)
             path.append((x, y))
        return path

    @staticmethod
    def get_random_scroll_amount():
        """Return a random pixel amount to scroll."""
        return random.randint(300, 800)

    @staticmethod
    def should_take_break(action_count):
        """
        Decide if the bot should take a longer break based on number of actions.
        Simulates a human getting tired or distracted.
        """
        if action_count > random.randint(10, 20):
             return True, random.randint(60, 300) # Break for 1-5 minutes
        return False, 0
