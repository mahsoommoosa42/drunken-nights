"""All game content: prompts, questions, words, categories, etc."""

import random
from typing import Any

# ─── Truth or Dare ───────────────────────────────────────────────────────────

TRUTHS = [
    "What's the most embarrassing thing you've done while drunk?",
    "What's the worst text you've ever sent to the wrong person?",
    "What's the biggest lie you've told to get out of plans?",
    "Who in this room would you least want to be stuck on an island with?",
    "What's the most ridiculous thing you've done to impress a crush?",
    "What's the weirdest thing you've Googled recently?",
    "What's a secret you've never told anyone in this room?",
    "What's the pettiest reason you've stopped talking to someone?",
    "If you could read one person's mind in this room, who would it be?",
    "What's the most cringe thing in your camera roll right now?",
    "What's the dumbest thing you've spent money on while drunk?",
    "Who was your worst kiss and why?",
    "What's your most embarrassing autocorrect fail?",
    "What's a red flag you totally ignored in a relationship?",
    "What's the longest you've gone without showering?",
    "What's the most childish thing you still do?",
    "Who in this room do you think is the worst driver?",
    "What's the worst date you've ever been on?",
    "What's the most awkward thing that happened to you at work/school?",
    "Have you ever pretended to be sick to avoid someone? Who?",
    "What's the most questionable thing in your search history?",
    "If your browser history was made public, what would be most embarrassing?",
    "What's a guilty pleasure you're embarrassed to admit?",
    "Who was the last person you stalked on social media?",
    "What's the most ridiculous excuse you've made up?",
    "What's something you've done that you'd judge someone else for?",
    "What's the worst gift you've ever received and pretended to like?",
    "Have you ever had a crush on a friend's partner?",
    "What's the most embarrassing thing your parents caught you doing?",
    "What's your most irrational fear?",
]

DARES = [
    "Take a sip and do your best impression of someone in the room.",
    "Let the group go through your last 10 photos. Take a sip for each embarrassing one.",
    "Call a random contact and sing Happy Birthday. Drink if they hang up.",
    "Post the 3rd last photo in your camera roll on your story for 1 hour or drink twice.",
    "Let someone in the group send a text from your phone. Drink regardless.",
    "Do your best drunk celebrity impression for 30 seconds.",
    "Talk in an accent for the next 3 rounds or take 2 sips.",
    "Give a dramatic 30-second speech about why pineapple belongs on pizza.",
    "Let the group pick your profile picture for 24 hours or drink 3 times.",
    "Dramatically reenact the last argument you had.",
    "Speak in only questions for the next 2 rounds. Drink when you fail.",
    "Give a compliment to everyone in the room. Drink for each awkward pause.",
    "Tell the room your most used emoji and explain why. Drink if it's embarrassing.",
    "Do your best TikTok dance. Drink twice if nobody recognizes it.",
    "Read your last sent text out loud to the group.",
    "Let the person to your right post anything they want on your social media.",
    "Serenade the person across from you with a love song.",
    "Talk without closing your mouth for 30 seconds. Drink if you fail.",
    "Share the last thing you copied on your clipboard.",
    "Give a 1-minute motivational speech about something completely mundane.",
    "Act out a movie scene and everyone has to guess. Drink if nobody gets it.",
    "Say something nice about every person in the room in a baby voice.",
    "Demonstrate your signature dance move. Everyone drinks if it's bad.",
    "Attempt to beatbox for 15 seconds. Drink if you can't keep a beat.",
    "Tell the group your screen time for this week. Drink for every hour over 4.",
]

# ─── Never Have I Ever ───────────────────────────────────────────────────────

NEVER_HAVE_I_EVER = [
    "Never have I ever sent a drunk text I deeply regret",
    "Never have I ever pretended to be someone else online",
    "Never have I ever eaten food off the floor",
    "Never have I ever lied on my resume",
    "Never have I ever ghosted someone",
    "Never have I ever cried at a movie in the theater",
    "Never have I ever been kicked out of a bar",
    "Never have I ever faked being sick to skip work/school",
    "Never have I ever re-gifted a present",
    "Never have I ever stalked an ex on social media",
    "Never have I ever gone skinny dipping",
    "Never have I ever forgotten someone's name right after meeting them",
    "Never have I ever accidentally liked a very old Instagram post while stalking",
    "Never have I ever broken something at someone's house and not told them",
    "Never have I ever walked into a glass door",
    "Never have I ever peed in a pool as an adult",
    "Never have I ever taken something from a hotel room",
    "Never have I ever pretended to laugh at a joke I didn't get",
    "Never have I ever been caught talking to myself",
    "Never have I ever had a wardrobe malfunction in public",
    "Never have I ever eaten an entire pizza by myself in one sitting",
    "Never have I ever forgotten a significant other's birthday",
    "Never have I ever tripped in public and pretended nothing happened",
    "Never have I ever read someone's messages without permission",
    "Never have I ever blamed a fart on someone else",
    "Never have I ever clogged someone else's toilet",
    "Never have I ever lied about my age",
    "Never have I ever watched a kids' show as an adult and enjoyed it",
    "Never have I ever been so hungover I swore I'd never drink again",
    "Never have I ever accidentally called a teacher 'mom' or 'dad'",
    "Never have I ever taken a selfie in the bathroom",
    "Never have I ever eaten something that fell in the sink",
    "Never have I ever had an imaginary friend past age 10",
    "Never have I ever worn the same underwear two days in a row",
    "Never have I ever waved back at someone who wasn't waving at me",
]

# ─── Would You Rather ────────────────────────────────────────────────────────

WOULD_YOU_RATHER = [
    ("Always have to speak in rhymes", "Always have to speak in song lyrics"),
    ("Have no filter for one full day", "Have everyone read your thoughts for one hour"),
    ("Give up your phone for a month", "Give up your bed for a month"),
    ("Be famous but always broke", "Be rich but nobody knows your name"),
    ("Relive high school", "Skip ahead to being 70"),
    ("Only eat one meal a day forever", "Never eat your favorite food again"),
    ("Have a rewind button for your life", "Have a pause button"),
    ("Know when you're going to die", "Know how you're going to die"),
    ("Fight 100 duck-sized horses", "Fight 1 horse-sized duck"),
    ("Always be 10 minutes late", "Always be 20 minutes early"),
    ("Lose the ability to read", "Lose the ability to speak"),
    ("Be able to fly but only 2 feet off the ground", "Be invisible but only when nobody's looking"),
    ("Have a permanent clown face", "Have a permanent clown laugh"),
    ("Have hands for feet", "Have feet for hands"),
    ("Always smell slightly like onions", "Always have a booger visible in your nose"),
    ("Give up Netflix forever", "Give up Spotify forever"),
    ("Have unlimited money but no friends", "Be broke but have the best friends"),
    ("Be allergic to your phone", "Be allergic to your favorite drink"),
    ("Always feel like you have to sneeze", "Always have a song stuck in your head"),
    ("Eat a tablespoon of hot sauce before every meal", "Drink a glass of pickle juice every morning"),
    ("Have everyone know your browser history", "Have everyone know your bank account balance"),
    ("Be stuck in an elevator with your ex", "Be stuck in an elevator with your boss"),
    ("Only whisper for the rest of your life", "Only shout for the rest of your life"),
    ("Give up social media forever", "Give up desserts forever"),
    ("Have a third eye on the back of your head", "Have an extra mouth on your forehead"),
]

# ─── Kings Cup Card Rules ────────────────────────────────────────────────────

KINGS_CUP_RULES: dict[str, dict[str, str]] = {
    "A":  {"name": "Waterfall",        "rule": "Everyone starts drinking. You can only stop when the person before you stops."},
    "2":  {"name": "You",              "rule": "Pick someone to drink."},
    "3":  {"name": "Me",               "rule": "You drink."},
    "4":  {"name": "Floor",            "rule": "Last person to touch the floor drinks."},
    "5":  {"name": "Guys",             "rule": "All guys drink."},
    "6":  {"name": "Chicks",           "rule": "All ladies drink."},
    "7":  {"name": "Heaven",           "rule": "Last person to raise their hand drinks."},
    "8":  {"name": "Mate",             "rule": "Pick a drinking buddy. They drink whenever you drink."},
    "9":  {"name": "Rhyme",            "rule": "Say a word. Go around rhyming it. First person who can't rhyme drinks."},
    "10": {"name": "Categories",       "rule": "Pick a category. Go around naming things in it. First person who repeats or blanks drinks."},
    "J":  {"name": "Rule Master",      "rule": "Make a rule everyone must follow. Anyone who breaks it drinks."},
    "Q":  {"name": "Question Master",  "rule": "You're the Question Master. Anyone who answers your questions drinks — until the next Queen is drawn."},
    "K":  {"name": "King's Cup",       "rule": "Pour some of your drink into the King's Cup. Whoever draws the 4th King drinks it all."},
}

SUITS = ["spades", "hearts", "diamonds", "clubs"]
SUIT_SYMBOLS = {"spades": "\u2660", "hearts": "\u2665", "diamonds": "\u2666", "clubs": "\u2663"}

# ─── Most Likely To ──────────────────────────────────────────────────────────

MOST_LIKELY_TO = [
    "Most likely to get lost in their own neighborhood",
    "Most likely to survive a zombie apocalypse",
    "Most likely to accidentally start a fire",
    "Most likely to become famous for something embarrassing",
    "Most likely to show up to the wrong event",
    "Most likely to fall asleep first at a party",
    "Most likely to marry a celebrity",
    "Most likely to text their ex tonight",
    "Most likely to get arrested for something stupid",
    "Most likely to cry during a commercial",
    "Most likely to go viral on social media",
    "Most likely to spend their rent money on something dumb",
    "Most likely to get into an argument with a stranger",
    "Most likely to forget their own birthday",
    "Most likely to talk their way out of a speeding ticket",
    "Most likely to win a hot dog eating contest",
    "Most likely to become a conspiracy theorist",
    "Most likely to accidentally join a cult",
    "Most likely to go on a reality TV show",
    "Most likely to get banned from a restaurant",
    "Most likely to adopt 10 cats",
    "Most likely to laugh at the worst possible time",
    "Most likely to bring up an embarrassing story in public",
    "Most likely to eat something off the ground",
    "Most likely to send a risky text and immediately regret it",
    "Most likely to have a secret talent nobody knows about",
    "Most likely to get into a fight over food",
    "Most likely to be the loudest person in any room",
    "Most likely to wake up in a completely different city",
    "Most likely to accidentally offend someone without realizing it",
]

# ─── Categories ──────────────────────────────────────────────────────────────

CATEGORIES = [
    "Types of beer",
    "Cocktail names",
    "Things you'd find in a bar",
    "Excuses for being late",
    "Things you shouldn't say to your boss",
    "Fast food chains",
    "Things that are green",
    "Things people do drunk they wouldn't do sober",
    "Celebrity DJs",
    "Types of shots",
    "Things you'd find at a house party",
    "Brands of vodka",
    "Things you regret buying",
    "Cartoon characters",
    "Pizza toppings",
    "Things you'd do if you were invisible",
    "Apps on your phone",
    "Things that come in pairs",
    "One-hit wonders",
    "Excuses for not texting back",
    "Breakfast cereals",
    "Things you'd bring to a desert island",
    "Types of cheese",
    "Things people lie about on dating apps",
    "Movie villains",
    "Things that smell bad",
    "Things you'd find in a college dorm",
    "Types of pasta",
    "Things you shouldn't do on a first date",
    "Reality TV shows",
]

# ─── Trivia ──────────────────────────────────────────────────────────────────

TRIVIA = [
    {"q": "What is the most popular cocktail in the world?", "options": ["Margarita", "Old Fashioned", "Mojito", "Martini"], "answer": 0},
    {"q": "Which country drinks the most beer per capita?", "options": ["Germany", "Czech Republic", "Ireland", "USA"], "answer": 1},
    {"q": "What is tequila made from?", "options": ["Corn", "Blue agave", "Sugarcane", "Potatoes"], "answer": 1},
    {"q": "What does IPA stand for?", "options": ["International Pale Ale", "India Pale Ale", "Irish Pale Ale", "Italian Pale Ale"], "answer": 1},
    {"q": "Which fruit is used to make a traditional daiquiri?", "options": ["Mango", "Strawberry", "Lime", "Pineapple"], "answer": 2},
    {"q": "What is the fear of alcohol called?", "options": ["Methyphobia", "Alcoholophobia", "Vinophobia", "Potophobia"], "answer": 0},
    {"q": "How many standard drinks are in a bottle of wine?", "options": ["3", "5", "7", "4"], "answer": 1},
    {"q": "What ingredient makes a Moscow Mule unique?", "options": ["Lime juice", "Ginger beer", "Vodka", "Mint"], "answer": 1},
    {"q": "Which country is famous for sake?", "options": ["China", "Korea", "Japan", "Thailand"], "answer": 2},
    {"q": "What does 'ABV' stand for?", "options": ["Alcohol Before Volume", "Alcohol By Volume", "Always Buy Vodka", "Ale Brewed Varietal"], "answer": 1},
    {"q": "What is the main ingredient in bourbon?", "options": ["Wheat", "Rye", "Corn", "Barley"], "answer": 2},
    {"q": "A 'flight' in bar terms refers to what?", "options": ["A drinking contest", "A sampler of drinks", "A type of glass", "Leaving without paying"], "answer": 1},
    {"q": "What gives gin its distinctive flavor?", "options": ["Hops", "Juniper berries", "Coriander", "Pine needles"], "answer": 1},
    {"q": "What cocktail is James Bond famous for ordering?", "options": ["Manhattan", "Martini", "Old Fashioned", "Negroni"], "answer": 1},
    {"q": "Which beer brand uses the slogan 'The King of Beers'?", "options": ["Heineken", "Budweiser", "Corona", "Miller"], "answer": 1},
    {"q": "What is a 'jigger' used for in bartending?", "options": ["Stirring", "Measuring", "Straining", "Shaking"], "answer": 1},
    {"q": "What country did champagne originate from?", "options": ["Italy", "Spain", "France", "Germany"], "answer": 2},
    {"q": "What is absinthe traditionally nicknamed?", "options": ["The Green Fairy", "The Black Mamba", "The Devil's Drink", "The Blue Moon"], "answer": 0},
    {"q": "What type of alcohol is in a Pina Colada?", "options": ["Vodka", "Tequila", "Rum", "Gin"], "answer": 2},
    {"q": "What does 'on the rocks' mean?", "options": ["Blended with ice", "Served with ice", "No ice", "Warm"], "answer": 1},
    {"q": "Which country produces the most wine?", "options": ["France", "Italy", "Spain", "USA"], "answer": 1},
    {"q": "What is the main spirit in a Cosmopolitan?", "options": ["Gin", "Rum", "Vodka", "Tequila"], "answer": 2},
    {"q": "What color is Midori liqueur?", "options": ["Blue", "Red", "Green", "Yellow"], "answer": 2},
    {"q": "How many bottles of champagne in a Nebuchadnezzar?", "options": ["6", "10", "15", "20"], "answer": 3},
    {"q": "What is a 'boilermaker'?", "options": ["A type of still", "Beer with a whiskey shot", "A heated cocktail", "A beer bong"], "answer": 1},
]

# ─── Hot Takes ───────────────────────────────────────────────────────────────

HOT_TAKES = [
    "Pineapple absolutely belongs on pizza",
    "Breakfast for dinner is better than dinner for dinner",
    "Dogs are overrated — cats are superior",
    "Social media has made the world a worse place",
    "Cold pizza is better than hot pizza",
    "It's okay to recline your seat on an airplane",
    "Ketchup on eggs is completely acceptable",
    "Beyonce is overrated",
    "Working from home is better than working in an office",
    "The toilet paper should go over, not under — always",
    "Water is not wet",
    "A hot dog IS a sandwich",
    "Tipping culture has gone too far",
    "Cereal is a soup",
    "It's fine to wear socks with sandals",
    "The book is NOT always better than the movie",
    "Astrology is complete nonsense",
    "GIF is pronounced with a hard G — always",
    "Naps are a waste of time",
    "The person who suggests the restaurant should pay",
    "It's okay to text 'k'",
    "Reality TV is actually good entertainment",
    "Brunch is overrated and overpriced",
    "Dark chocolate is superior to milk chocolate",
    "You should shower at night, not in the morning",
    "Being early is just as rude as being late",
    "Ranch goes on everything",
    "Summer is the worst season",
    "New Year's Eve is the most overrated holiday",
    "Sparkling water is just angry water and it's gross",
]

# ─── Taboo ───────────────────────────────────────────────────────────────────

TABOO_WORDS = [
    {"word": "Hangover", "forbidden": ["Drink", "Morning", "Headache", "Alcohol", "Party"]},
    {"word": "Karaoke", "forbidden": ["Sing", "Song", "Microphone", "Bar", "Music"]},
    {"word": "Selfie", "forbidden": ["Photo", "Camera", "Phone", "Picture", "Snap"]},
    {"word": "Netflix", "forbidden": ["Stream", "Watch", "Show", "Movie", "Chill"]},
    {"word": "Tinder", "forbidden": ["Swipe", "Date", "Match", "App", "Love"]},
    {"word": "Pizza", "forbidden": ["Cheese", "Slice", "Delivery", "Italian", "Pepperoni"]},
    {"word": "Uber", "forbidden": ["Ride", "Car", "Driver", "App", "Taxi"]},
    {"word": "Tattoo", "forbidden": ["Ink", "Skin", "Needle", "Body", "Permanent"]},
    {"word": "Beach", "forbidden": ["Sand", "Ocean", "Water", "Sun", "Wave"]},
    {"word": "Meme", "forbidden": ["Funny", "Internet", "Picture", "Viral", "Share"]},
    {"word": "Brunch", "forbidden": ["Breakfast", "Lunch", "Morning", "Eggs", "Mimosa"]},
    {"word": "Gym", "forbidden": ["Exercise", "Workout", "Lift", "Fit", "Muscle"]},
    {"word": "Snapchat", "forbidden": ["Snap", "Photo", "Filter", "Story", "Send"]},
    {"word": "Coachella", "forbidden": ["Music", "Festival", "Desert", "California", "Concert"]},
    {"word": "Avocado", "forbidden": ["Green", "Guacamole", "Toast", "Fruit", "Mexican"]},
    {"word": "Champagne", "forbidden": ["Bubbles", "Wine", "Celebrate", "Toast", "French"]},
    {"word": "Podcast", "forbidden": ["Listen", "Audio", "Episode", "Show", "Talk"]},
    {"word": "Road Trip", "forbidden": ["Drive", "Car", "Travel", "Highway", "Journey"]},
    {"word": "Halloween", "forbidden": ["Costume", "Scary", "October", "Candy", "Pumpkin"]},
    {"word": "TikTok", "forbidden": ["Video", "Dance", "App", "Short", "Viral"]},
    {"word": "Margarita", "forbidden": ["Tequila", "Salt", "Lime", "Cocktail", "Mexican"]},
    {"word": "Sushi", "forbidden": ["Fish", "Rice", "Japanese", "Roll", "Raw"]},
    {"word": "Concert", "forbidden": ["Music", "Band", "Live", "Stage", "Tickets"]},
    {"word": "Sunburn", "forbidden": ["Sun", "Red", "Skin", "Burn", "Beach"]},
    {"word": "Gossip", "forbidden": ["Talk", "Secret", "Rumor", "Tell", "Drama"]},
    {"word": "Hangout", "forbidden": ["Friends", "Meet", "Chill", "Together", "Fun"]},
    {"word": "Influencer", "forbidden": ["Social", "Follow", "Famous", "Instagram", "Brand"]},
    {"word": "Karate", "forbidden": ["Martial", "Kick", "Belt", "Fight", "Art"]},
    {"word": "Barbecue", "forbidden": ["Grill", "Meat", "Cook", "Outside", "Summer"]},
    {"word": "Whiskey", "forbidden": ["Bourbon", "Drink", "Alcohol", "Shot", "Barrel"]},
]

# ─── Two Truths and a Lie — starter prompts ─────────────────────────────────

TWO_TRUTHS_PROMPTS = [
    "Think of two TRUE things and one LIE about your childhood.",
    "Think of two TRUE things and one LIE about your love life.",
    "Think of two TRUE things and one LIE about your worst habits.",
    "Think of two TRUE things and one LIE about embarrassing moments.",
    "Think of two TRUE things and one LIE about things you've eaten.",
    "Think of two TRUE things and one LIE about your job/school.",
    "Think of two TRUE things and one LIE about your travels.",
    "Think of two TRUE things and one LIE about your biggest fears.",
    "Think of two TRUE things and one LIE about your guilty pleasures.",
    "Think of two TRUE things and one LIE about things you've broken.",
    "Think of two TRUE things and one LIE about your teenage years.",
    "Think of two TRUE things and one LIE about your family.",
    "Think of two TRUE things and one LIE about concerts you've attended.",
    "Think of two TRUE things and one LIE about your phone habits.",
    "Think of two TRUE things and one LIE about things you've lost.",
]

# ─── Rhyme Time ──────────────────────────────────────────────────────────────

RHYME_STARTERS = [
    "cat", "blue", "night", "fun", "beer", "cake", "dance", "gold",
    "ring", "star", "light", "smoke", "drink", "lime", "beat", "chill",
    "rock", "day", "green", "hot", "cool", "fire", "rain", "high",
    "ride", "game", "fly", "loud", "dream", "wine",
]

# ─── Word Association ────────────────────────────────────────────────────────

WORD_ASSOCIATION_STARTERS = [
    "Party", "Drunk", "Shot", "Music", "Dance", "Love", "Beach",
    "Money", "Sleep", "Smoke", "Pizza", "Regret", "Selfie", "Kiss",
    "Secret", "Wild", "Midnight", "Vegas", "Dare", "Crazy",
    "Guilty", "Rumor", "Cheers", "Chaos", "Lit",
]


# ─── Helper to get random items without immediate repeats ────────────────────

class ShuffledDeck:
    """Draw items from a list without repeating until all are used."""

    def __init__(self, items: list[Any]) -> None:
        self._items = list(items)
        self._deck: list[Any] = []

    def draw(self) -> Any:
        if not self._deck:
            self._deck = list(self._items)
            random.shuffle(self._deck)
        return self._deck.pop()

    def draw_n(self, n: int) -> list[Any]:
        return [self.draw() for _ in range(n)]
