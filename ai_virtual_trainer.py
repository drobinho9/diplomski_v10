# ai_virtual_trainer.py -

import os
import json
import random
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from langdetect import detect


class AIVirtualTrainer:
    """AI trener koji može analizirati i zapisati podatke iz razgovora"""

    def __init__(self, user_dict: dict, db_session=None, models=None):
        self.user = user_dict
        self.db = db_session
        self.models = models  # WorkoutLog, MealLog, MoodLog modeli
        self.conversation_history = []
        self._load_model()

    def _load_model(self):
        """Učitaj DialoGPT model"""
        try:
            print("🤖 Učitavam AI model...")
            model_name = "microsoft/DialoGPT-medium"
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.history = []
            print("✅ AI model uspješno učitan!")

        except Exception as e:
            print(f"❌ Greška pri učitavanju AI modela: {e}")
            self.model = None
            self.tokenizer = None
            self.history = []

    def analyze_and_save_message(self, user_message: str, user_id: int) -> dict:
        """
        Analiziraj korisničku poruku i automatski spremi prepoznate podatke u bazu
        """
        analysis_result = {
            'exercises_saved': 0,
            'meals_saved': 0,
            'mood_saved': False,
            'water_saved': 0,
            'recognized_data': {
                'exercises': [],
                'food': [],
                'mood': 'neutral',
                'water': 0,
                'warnings': []
            }
        }

        if not user_message.strip():
            return analysis_result


        recognized = self._extract_fitness_data(user_message)
        analysis_result['recognized_data'] = recognized


        if self.db and self.models:
            try:
                # Spremi vježbe
                for exercise_data in recognized['exercises']:
                    workout = self.models['WorkoutLog'](
                        user_id=user_id,
                        exercise=exercise_data['name'],
                        sets=exercise_data.get('sets', 1),
                        reps=exercise_data.get('reps', 1),
                        weight=exercise_data.get('weight', None),
                        feeling=recognized['mood']
                    )
                    self.db.add(workout)
                    analysis_result['exercises_saved'] += 1

                # Spremi hranu
                for food_data in recognized['food']:
                    meal = self.models['MealLog'](
                        user_id=user_id,
                        food=food_data['name'],
                        calories=food_data.get('calories', 100),
                        liked_recommendation=True
                    )
                    self.db.add(meal)
                    analysis_result['meals_saved'] += 1

                # Spremi raspoloženje
                if recognized['mood'] != 'neutral':
                    mood = self.models['MoodLog'](
                        user_id=user_id,
                        mood='good' if recognized['mood'] == 'positive' else 'bad',
                        note=user_message[:200]
                    )
                    self.db.add(mood)
                    analysis_result['mood_saved'] = True

                # Spremi vodu
                if recognized['water'] > 0:
                    water = self.models['WaterLog'](
                        user_id=user_id,
                        amount_ml=recognized['water']
                    )
                    self.db.add(water)
                    analysis_result['water_saved'] = recognized['water']

                self.db.commit()
                print(f"✅ Uspješno spremljeno: {analysis_result}")

            except Exception as e:
                self.db.rollback()
                print(f"❌ Greška pri spremanju u bazu: {e}")

        return analysis_result

    def _extract_fitness_data(self, text: str) -> dict:
        """Izvuci fitness podatke iz teksta"""
        result = {
            'exercises': [],
            'food': [],
            'mood': 'neutral',
            'water': 0,
            'warnings': []
        }

        text_lower = text.lower()


        exercise_patterns = {
            r'(?:napravio|radio|trenirao).*?(?:čučanj|squat).*?(?:(\d+)[x×](\d+))?.*?(?:(\d+)\s*kg)?': 'Squat',
            r'(?:napravio|radio|trenirao).*?(?:mrtvo\s*dizanje|deadlift).*?(?:(\d+)[x×](\d+))?.*?(?:(\d+)\s*kg)?': 'Deadlift',
            r'(?:napravio|radio|trenirao).*?(?:bench\s*press|potisak).*?(?:(\d+)[x×](\d+))?.*?(?:(\d+)\s*kg)?': 'Bench Press',
            r'(?:napravio|radio|trenirao).*?(?:zgib|pull.*?up).*?(?:(\d+)[x×](\d+))?': 'Pull-ups',
            r'(?:napravio|radio|trenirao).*?(?:sklekovi|push.*?up).*?(?:(\d+)[x×](\d+))?': 'Push-ups',
            r'(?:napravio|radio|trenirao).*?(?:iskorak|lunge).*?(?:(\d+)[x×](\d+))?.*?(?:(\d+)\s*kg)?': 'Lunges',
            r'(?:napravio|radio|trenirao).*?(?:plank).*?(?:(\d+)\s*(?:min|minuta))?': 'Plank',
            r'(?:trčao|trčanje|cardio).*?(?:(\d+)\s*(?:min|minuta|km))?': 'Cardio',
            r'(?:bicikl|cycling).*?(?:(\d+)\s*(?:min|minuta|km))?': 'Cycling',
            r'(?:plivanje|swimming).*?(?:(\d+)\s*(?:min|minuta))?': 'Swimming'
        }

        for pattern, exercise_name in exercise_patterns.items():
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                exercise = {'name': exercise_name}

                # Pokušaj izvući brojeve (sets x reps ili vrijeme)
                numbers = [int(g) for g in match.groups() if g and g.isdigit()]
                if len(numbers) >= 2:
                    exercise['sets'] = numbers[0]
                    exercise['reps'] = numbers[1]
                elif len(numbers) == 1:
                    if 'min' in text_lower:
                        exercise['duration_min'] = numbers[0]
                    elif 'km' in text_lower:
                        exercise['distance_km'] = numbers[0]
                    else:
                        exercise['reps'] = numbers[0]


                weight_match = re.search(r'(\d+)\s*kg', match.group())
                if weight_match:
                    exercise['weight'] = int(weight_match.group(1))

                result['exercises'].append(exercise)


        food_patterns = {

            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:jaja|jaje)': {'name': 'Jaja', 'calories': 155},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:piletina|piletinu)': {'name': 'Piletina', 'calories': 165},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:riba|ribu)': {'name': 'Riba', 'calories': 140},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:govedina|govedinu)': {'name': 'Govedina', 'calories': 200},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:svinjina|svinjetina)': {'name': 'Svinjina', 'calories': 180},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:tuna|tunu)': {'name': 'Tuna', 'calories': 130},


            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:riža|rižu)': {'name': 'Riža', 'calories': 130},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:krumpir)': {'name': 'Krumpir', 'calories': 110},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:tjestenina|pašta)': {'name': 'Tjestenina', 'calories': 150},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:kruh)': {'name': 'Kruh', 'calories': 80},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:zobene|ovsene|pahuljice)': {'name': 'Zobene pahuljice',
                                                                                      'calories': 120},


            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:salata|salatu)': {'name': 'Salata', 'calories': 20},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:rajčica|rajčice)': {'name': 'Rajčica', 'calories': 25},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:krastavac)': {'name': 'Krastavac', 'calories': 15},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:brokula|brokuli)': {'name': 'Brokula', 'calories': 30},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:špinat)': {'name': 'Špinat', 'calories': 25},

            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:banana|bananu)': {'name': 'Banana', 'calories': 105},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:jabuka|jabuku)': {'name': 'Jabuka', 'calories': 80},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:naranča|narandžu)': {'name': 'Naranča', 'calories': 65},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:avokado)': {'name': 'Avokado', 'calories': 160},


            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:jogurt)': {'name': 'Jogurt', 'calories': 100},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:sir)': {'name': 'Sir', 'calories': 110},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:mlijeko)': {'name': 'Mlijeko', 'calories': 150},


            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:orah|orahi)': {'name': 'Orahi', 'calories': 185},
            r'(?:jeo|pojeo|doručkovao|ručao|večerao).*?(?:badem|bademi)': {'name': 'Bademi', 'calories': 170},
        }

        for pattern, food_info in food_patterns.items():
            if re.search(pattern, text_lower):
                result['food'].append(food_info)


        positive_words = ['odličo', 'super', 'sjajno', 'fantastično', 'motiviran', 'energičan', 'dobro']
        negative_words = ['loše', 'umorno', 'tužno', 'frustriran', 'boli', 'pain', 'depresivno']

        for word in positive_words:
            if word in text_lower:
                result['mood'] = 'positive'
                break

        for word in negative_words:
            if word in text_lower:
                result['mood'] = 'negative'
                break


        water_patterns = [
            r'(?:popio|pio|pila).*?(\d+)\s*(?:litara|litre|l)\s*vode',
            r'(\d+)\s*(?:litara|litre|l)\s*vode',
            r'(?:popio|pio|pila).*?(\d+)\s*(?:čaša|čaše|čašu)\s*vode',
            r'(\d+)\s*(?:ml|mililitra)\s*vode'
        ]

        for pattern in water_patterns:
            match = re.search(pattern, text_lower)
            if match:
                amount = int(match.group(1))
                if 'ml' in match.group(0):
                    result['water'] = amount
                elif 'čaš' in match.group(0):
                    result['water'] = amount * 250  # 250ml po čaši
                else:  # litri
                    result['water'] = amount * 1000
                break


        if 'bol' in text_lower or 'pain' in text_lower:
            result['warnings'].append('pain_detected')
        if 'umoran' in text_lower or 'tired' in text_lower:
            result['warnings'].append('fatigue_detected')

        return result

    @torch.inference_mode()
    def generate_response(self, user_message: str, analysis_result: dict = None) -> str:
        """Generiraj AI odgovor na temelju poruke i analize"""

        if not self.model:
            return self._fallback_response(user_message, analysis_result)


        context = self._build_context_with_analysis(user_message, analysis_result)

        try:

            input_text = context + "\n\nKorisnik: " + user_message + "\nTrener:"
            input_ids = self.tokenizer.encode(input_text, return_tensors='pt', max_length=1000, truncation=True)

            if self.history:
                input_ids = torch.cat([torch.tensor([self.history]).to(input_ids.device), input_ids], dim=1)


            output_ids = self.model.generate(
                input_ids,
                max_length=input_ids.shape[1] + 150,
                do_sample=True,
                top_p=0.9,
                temperature=0.75,
                pad_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=1.2
            )


            new_tokens = output_ids[:, input_ids.shape[1]:]
            response = self.tokenizer.decode(new_tokens[0], skip_special_tokens=True).strip()

            self.history = output_ids[0].tolist()[-500:]  # zadnjih 500 tokena

            # Postprocess odgovor
            response = self._postprocess_response(response, analysis_result)

            return response

        except Exception as e:
            print(f"Greška u AI generiranju: {e}")
            return self._fallback_response(user_message, analysis_result)

    def _build_context_with_analysis(self, user_message: str, analysis_result: dict) -> str:
        """Izgradi kontekst koji uključuje informacije o prepoznatim podacima"""
        name = self.user.get('name', 'prijatelju')
        goal = self.user.get('goal', 'general fitness').replace('_', ' ')

        context = f"Ti si iskusan fitness trener koji pomaže korisniku {name}. "
        context += f"Cilj korisnika je {goal}. "

        if analysis_result:
            if analysis_result['exercises_saved'] > 0:
                context += f"Upravo je zabilježeno {analysis_result['exercises_saved']} vježbi. "
            if analysis_result['meals_saved'] > 0:
                context += f"Upravo je zabilježeno {analysis_result['meals_saved']} obroka. "
            if analysis_result['water_saved'] > 0:
                context += f"Upravo je zabilježeno {analysis_result['water_saved']}ml vode. "
            if analysis_result['mood_saved']:
                context += "Upravo je zabilježeno raspoloženje. "

        context += "Odgovori kratko, konkretno i motivirajuće na hrvatskom jeziku. "

        return context

    def _postprocess_response(self, response: str, analysis_result: dict) -> str:
        """Postprocess AI odgovor"""
        # Ukloni čudne znakove i skrati ako je predugačak
        response = re.sub(r'[^\w\s.,!?()-čćžšđČĆŽŠĐ]', '', response)
        response = response.strip()

        # Dodaj informacije o spremljenim podacima
        if analysis_result:
            saved_info = []
            if analysis_result['exercises_saved'] > 0:
                saved_info.append(f"✅ {analysis_result['exercises_saved']} vježbi")
            if analysis_result['meals_saved'] > 0:
                saved_info.append(f"✅ {analysis_result['meals_saved']} obroka")
            if analysis_result['water_saved'] > 0:
                saved_info.append(f"✅ {analysis_result['water_saved']}ml vode")
            if analysis_result['mood_saved']:
                saved_info.append("✅ raspoloženje")

            if saved_info:
                response += f"\n\n📝 **Automatski spremljeno:** {', '.join(saved_info)}"

        # Dodaj motivaciju na kraju
        motivational_endings = [
            "Nastavi tako! 💪",
            "Odličan posao! 🏆",
            "Svaki korak je napredak! 🚀",
            "Vjerujem u tebe! ⭐",
            "Ti možeš! 🔥"
        ]

        if random.random() < 0.4:  # 40% šanse za motivaciju
            response += " " + random.choice(motivational_endings)

        return response

    def _fallback_response(self, user_message: str, analysis_result: dict) -> str:
        """Rezervni odgovor kad AI ne radi"""
        name = self.user.get('name', 'prijatelju')

        # Odgovor na temelju prepoznatih podataka
        if analysis_result:
            responses = []

            if analysis_result['exercises_saved'] > 0:
                responses.append(f"Bravo, {name}! Zabilježio sam tvoje vježbe.")

            if analysis_result['meals_saved'] > 0:
                responses.append(f"Odličo, {name}! Spremio sam podatke o hrani.")

            if analysis_result['water_saved'] > 0:
                responses.append(f"Super, {name}! Hidratacija je važna.")

            if analysis_result['mood_saved']:
                responses.append(f"Hvala što dijeliš svoje raspoloženje, {name}.")

            if responses:
                return " ".join(responses) + " Nastavi tako! 💪"

        # Općeniti odgovor
        return f"Hvala na poruci, {name}! Kako ti mogu pomoći s treningom i prehranom?"


class TrainerChat:
    """Wrapper klasa za lakšu integraciju s Flask aplikacijom"""

    def __init__(self, user, db_session, models):
        self.user = user
        self.db = db_session
        self.models = models
        self.trainer = AIVirtualTrainer({
            'name': user.username,
            'age': user.age or 25,
            'goal': user.goal or 'maintenance',
            'fitness_level': user.fitness_level or 'beginner'
        }, db_session, models)

    def process_message(self, message: str) -> dict:
        """
        Procesira korisničku poruku:
        1. Analizira i sprema podatke u bazu
        2. Generiraj AI odgovor
        3. Vrati rezultat
        """
        # Analiziraj i spremi podatke
        analysis_result = self.trainer.analyze_and_save_message(message, self.user.id)

        # Generiraj AI odgovor
        ai_response = self.trainer.generate_response(message, analysis_result)

        return {
            'ai_response': ai_response,
            'analysis_result': analysis_result,
            'saved_data': {
                'exercises': analysis_result['exercises_saved'],
                'meals': analysis_result['meals_saved'],
                'mood': analysis_result['mood_saved'],
                'water': analysis_result['water_saved']
            }
        }
