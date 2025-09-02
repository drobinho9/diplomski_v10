# a_07_nutrition_rl_agent.py (Konačna verzija sa spremanjem)
import sys
import os
import numpy as np
import random
import joblib


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ''))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("--- KORAK 7: RAZVOJ I SPREMANJE NUTRICIONISTIČKOG RL AGENTA ---")



class NutritionEnvironment:
    def __init__(self):
        self.state = (0, 0)
        self.done = False

    def reset(self):
        self.state = (0, random.choice([0, 1]))
        self.done = False
        return self.state

    def step(self, action):
        if self.done:
            raise ValueError("Dan je gotov, morate pozvati reset().")
        time_of_day, last_meal_type = self.state
        reward = 0
        if time_of_day == 0:
            if action == 1:
                reward = 10
            else:
                reward = -5
        elif time_of_day == 1:
            reward = 5
        elif time_of_day == 2:
            if action == 0:
                reward = 10
            else:
                reward = -10
        new_time_of_day = time_of_day + 1
        new_last_meal_type = action
        if new_time_of_day > 2:
            self.done = True
        self.state = (new_time_of_day, new_last_meal_type)
        return self.state, reward, self.done


class QLearningAgent:
    def __init__(self, num_states_time, num_states_meal, num_actions, learning_rate=0.1, discount_factor=0.9,
                 epsilon=1.0):
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = 0.999
        self.epsilon_min = 0.01
        self.q_table = np.zeros((num_states_time, num_states_meal, num_actions))

    def choose_action(self, state):
        if random.uniform(0, 1) < self.epsilon:
            return random.choice([0, 1])
        else:
            time_of_day, last_meal_type = state
            return np.argmax(self.q_table[time_of_day, last_meal_type])

    def learn(self, state, action, reward, next_state):
        time_of_day, last_meal_type = state
        next_time_of_day, _ = next_state
        old_value = self.q_table[time_of_day, last_meal_type, action]
        if next_time_of_day > 2:
            next_max = 0
        else:
            next_max = np.max(self.q_table[next_time_of_day])
        new_value = (1 - self.lr) * old_value + self.lr * (reward + self.gamma * next_max)
        self.q_table[time_of_day, last_meal_type, action] = new_value
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay



if __name__ == '__main__':
    env = NutritionEnvironment()
    agent = QLearningAgent(num_states_time=3, num_states_meal=2, num_actions=2)
    num_episodes = 10000

    print("\n--- Započinjem treniranje agenta ---")
    for episode in range(num_episodes):
        state = env.reset()
        done = False
        while not done:
            action = agent.choose_action(state)
            next_state, reward, done = env.step(action)
            agent.learn(state, action, reward, next_state)
            state = next_state
        if (episode + 1) % 2000 == 0:
            print(f"Epizoda {episode + 1}/{num_episodes} završena.")

    print("--- Treniranje završeno! ---")

    MODELS_PATH = 'models'
    os.makedirs(MODELS_PATH, exist_ok=True)  # Osiguraj da 'models' direktorij postoji
    AGENT_PATH = os.path.join(MODELS_PATH, 'nutrition_rl_agent.joblib')
    joblib.dump(agent, AGENT_PATH)
    print(f"\n -> Istrenirani RL agent je uspješno spremljen u: {AGENT_PATH}")
    # =================================================================================