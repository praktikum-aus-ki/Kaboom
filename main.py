import gymnasium as gym
import ale_py

# Create Kaboom environment
env = gym.make("ALE/Kaboom-v5", render_mode="human")  # render_mode="human" opens a window
obs, info = env.reset(seed=42)

done = False
while not done:
    # Render the environment
    env.render()

    # Random action just to see the game
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated

env.close()