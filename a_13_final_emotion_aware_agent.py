# a_13_final_emotion_aware_agent.py
import numpy as np
import random
import os
import joblib

# Kod za popravak importa
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ''))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import User
from transformers import pipeline
from langdetect import detect, LangDetectException

print("--- KORAK 13: TRENIRANJE FINALNOG, EMOCIONALNO SVJESNOG RL AGENTA ---")

# --- 1. Učitavanje Modela za Emocije ---
print("Učitavam modele za analizu teksta...")
try:
    emotion_classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", top_k=1)
    sentiment_classifier = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")
    print("-> Modeli za emocije/sentiment uspješno učitani.")
except Exception as e:
    print(f"GREŠKA pri učitavanju NLP modela: {e}")
    emotion_classifier = sentiment_classifier = None

def analyze_bilingual_emotion(text):
    if not text: return "neutral"
    try:
        lang = detect(text)
        if lang == 'en' and emotion_classifier:
            return emotion_classifier(text)[0][0]['label']
        elif sentiment_classifier:
            result = sentiment_classifier(text)[0]
            score = int(result['label'].split()[0])
            if score <= 2: return 'negative'
            elif score == 3: return 'neutral'
            else: return 'positive'
        return "neutral"
    except LangDetectException:
        return "neutral"

# --- 2. Definiranje Finalnog Okruženja (V4) ---
class NutritionEnvironmentV4:
    def __init__(self, user, workout_plan_structure):
        self.user, self.workout_plan_structure = user, workout_plan_structure
        self.tdee = self._calculate_tdee()
        self.state_space_shape = (7, 3, 3, 3)
        self.action_space_size = 3
        self.emotion_map = {'positive': 0, 'joy': 0, 'love': 0, 'surprise': 0, 'neutral': 1, 'negative': 2, 'sadness': 2, 'anger': 2, 'fear': 2}
        self.reset(0)

    def _calculate_tdee(self):
        s = 5 if self.user.gender == 'male' else -161
        bmr = (10 * self.user.weight) + (6.25 * self.user.height) - (5 * self.user.age) + s
        multiplier = {'beginner': 1.375, 'intermediate': 1.55, 'advanced': 1.725}.get(self.user.fitness_level, 1.55)
        return bmr * multiplier

    def _get_caloric_status(self):
        ratio = self.calories_consumed_today / self.tdee
        if ratio < 0.85: return 0
        if ratio <= 1.15: return 1
        return 2

    def reset(self, episode_num):
        self.day_of_week = episode_num % 7
        self.time_of_day = 0
        self.calories_consumed_today = 0
        self.user_goal = {'weight_loss': 0, 'maintenance': 1, 'muscle_gain': 2}.get(self.user.goal)
        self.done = False
        self.current_emotion_text = random.choice(["I feel great today", "I am so sad", "Just a regular day"])
        emotion = analyze_bilingual_emotion(self.current_emotion_text)
        self.current_emotion_idx = self.emotion_map.get(emotion, 1)
        return (self.day_of_week, self.user_goal, self._get_caloric_status(), self.current_emotion_idx)

    def step(self, action):
        meal_calories = [300, 600, 900][action]
        self.calories_consumed_today += meal_calories
        is_training_day = "Odmor" not in self.workout_plan_structure.get(self.day_of_week, "Odmor")
        reward = 0
        current_status = self._get_caloric_status()
        if self.user_goal == 0:
            if current_status == 0: reward += 15
            elif current_status == 1: reward += -5 if not is_training_day else 5
            else: reward += -20 if not is_training_day else -10
        elif self.user_goal == 1:
            reward += 15 if current_status == 1 else -10
        elif self.user_goal == 2:
            if current_status == 2: reward += 15 if is_training_day else 10
            elif current_status == 1: reward += 5
            else: reward += -20
        if self.current_emotion_idx == 2:
            if action == 1: reward += 10
            elif action == 0: reward += -5
        elif self.current_emotion_idx == 0:
            if action == 0: reward += 10
        self.time_of_day += 1
        if self.time_of_day >= 3: self.done = True
        self.current_emotion_text = random.choice(["I feel great today", "I am so sad", "Just a regular day"])
        emotion = analyze_bilingual_emotion(self.current_emotion_text)
        self.current_emotion_idx = self.emotion_map.get(emotion, 1)
        next_state = (self.day_of_week, self.user_goal, self._get_caloric_status(), self.current_emotion_idx)
        return next_state, reward, self.done

# =============================== KLJUČAN POPRAVAK OVDJE ===============================
# Dodajemo definiciju klase koju smo zaboravili
class QLearningAgentV3:
    def __init__(self, state_shape, action_size, learning_rate=0.1, discount_factor=0.9, epsilon=1.0):
        self.lr, self.gamma, self.epsilon = learning_rate, discount_factor, epsilon
        self.epsilon_decay, self.epsilon_min = 0.99995, 0.01
        self.q_table = np.zeros(state_shape + (action_size,))
    def choose_action(self, state):
        if random.uniform(0, 1) < self.epsilon:
            return random.randrange(self.q_table.shape[-1])
        else:
            return np.argmax(self.q_table[state])
    def learn(self, state, action, reward, next_state, done):
        old_value = self.q_table[state][action]
        next_max = np.max(self.q_table[next_state]) if not done else 0
        new_value = (1 - self.lr) * old_value + self.lr * (reward + self.gamma * next_max)
        self.q_table[state][action] = new_value
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
# ====================================================================================

class QLearningAgentV4(QLearningAgentV3):
    pass

# --- 3. Proces Treniranja ---
if __name__ == '__main__':
    test_user = User(username='final_user', age=30, gender='male', height=180, weight=85,
                     goal='weight_loss', # << MIJENJAJTE OVO
                     fitness_level='intermediate')
    workout_days = {0: "Trening", 1: "Trening", 2: "Odmor", 3: "Trening", 4: "Trening", 5: "Odmor", 6: "Odmor"}
    env = NutritionEnvironmentV4(user=test_user, workout_plan_structure=workout_days)
    agent = QLearningAgentV4(state_shape=env.state_space_shape, action_size=env.action_space_size)
    num_episodes = 100000
    print(f"\n--- Započinjem FINALNO treniranje za korisnika s ciljem: {test_user.goal} ---")
    for episode in range(num_episodes):
        state = env.reset(episode)
        done = False
        while not done:
            action = agent.choose_action(state)
            next_state, reward, done = env.step(action)
            agent.learn(state, action, reward, next_state, done)
            state = next_state
        if (episode + 1) % 10000 == 0:
            print(f"Epizoda {episode + 1}/{num_episodes} završena.")
    print("--- Treniranje završeno! ---")
    MODELS_PATH = 'models'
    os.makedirs(MODELS_PATH, exist_ok=True)
    AGENT_PATH = os.path.join(MODELS_PATH, f'final_rl_agent_{test_user.goal}.joblib')
    joblib.dump(agent, AGENT_PATH)
    print(f"\n -> FINALNI RL agent spremljen u: {AGENT_PATH}")

