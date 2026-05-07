# -*- coding: utf-8 -*-
"""Hashtag Generator — uses shared gemini_client (auto-detected model)."""

import os
import json
import re
from typing import List
from modules.gemini_client import get_model

BANKS = {
    "Music Performance": ["#guitarplayer","#guitarcover","#acousticguitar","#musicperformance","#guitarist","#livemusic","#musicreels","#originalmusic","#indiemusic","#musicianlife","#guitartok","#acousticcover","#newmusic","#singersongwriter","#musiciansofinstagram","#guitarsolos","#musicvideo","#reelsmusic","#guitarlessons","#rockguitar","#electricguitar","#jazzguitar","#fingerstyleguitar","#performanceartist","#localmusician"],
    "Sports": ["#sports","#athlete","#training","#sportsmotivation","#sportsreels","#athletelife","#competition","#sportsvideo","#gameday","#sportsedits","#athletetraining","#sportsmoments","#sportshighlights","#hustle","#sportslife","#sportscommunity","#workoutmotivation","#dedication","#teamwork","#sportsworld","#sportsman","#sportsgirl","#sportstime","#winning","#sportslover"],
    "Fitness": ["#fitness","#workout","#gym","#fitnessmotivation","#gymlife","#fitlife","#training","#bodybuilding","#fitnessjourney","#exercise","#homeworkout","#strength","#gains","#fitnessreels","#workoutreels","#personaltrainer","#calisthenics","#cardio","#legday","#chestday","#healthylifestyle","#fitnesscommunity","#gymrat","#fitnessgirl","#sweat"],
    "Tech Review": ["#techreview","#tech","#technology","#gadgets","#smartphone","#techunboxing","#techtok","#gadgetreview","#technews","#techgeek","#apple","#android","#techcommunity","#gadgetlover","#techreels","#newtech","#techlife","#innovation","#devicereview","#phonereviews","#techdaily","#techinfluencer","#gadgetworld","#techlovers","#techupdates"],
    "Dance": ["#dance","#dancer","#dancing","#choreography","#dancelife","#dancereels","#dancevideos","#dancechallenge","#hiphop","#dancecommunity","#choreographer","#dancecover","#dancetok","#viral","#dancetrend","#choreographyvideo","#danceislife","#danceperformance","#streetdance","#breakdance","#latinodance","#dancemoves","#dancestudio","#danceclass","#dancefloor"],
    "Gaming": ["#gaming","#gamer","#videogames","#gamingcommunity","#gamingreels","#gameplay","#streamer","#pcgaming","#consolegaming","#gaminglife","#gamingsetup","#esports","#twitch","#gamingmemes","#gamingvideos","#gamesofinstagram","#gamingcontent","#xbox","#playstation","#nintendoswitch","#gamertok","#gamingclips","#gamingmoments","#gamingfunny","#gamertag"],
    "Food & Cooking": ["#food","#cooking","#recipe","#foodreels","#cookingtok","#foodie","#homecooking","#foodvideo","#easyrecipes","#mealprep","#foodlover","#foodphotography","#cookingvideo","#foodblogger","#recipeoftheday","#homemade","#foodinstagram","#yummy","#delicious","#cookingathome","#foodreelsviral","#whatieatinaday","#healthyfood","#quickrecipes","#foodtok"],
    "Tutorial": ["#tutorial","#howto","#tips","#learning","#diy","#tutorialvideo","#tipsandtricks","#howtovideo","#stepbystep","#learnontiktok","#educational","#skillshare","#lifehacks","#productivitytips","#howtoreels","#techhacks","#learnsomething","#diytutorial","#tutorials","#quicktips","#masterclass","#learnwithtiktok","#knowledge","#facts","#explainer"],
    "Travel": ["#travel","#travelreels","#wanderlust","#travelphotography","#travelgram","#travelblogger","#explore","#adventure","#travellife","#travelvideos","#traveltok","#worldtravel","#traveldiaries","#travelvlog","#destination","#nomad","#traveljunkie","#traveltheworld","#beautifuldestinations","#exploremore","#travelcommunity","#traveltips","#instatravel","#travelstories","#globetrotter"],
    "Education": ["#education","#learning","#knowledge","#facts","#didyouknow","#eduTok","#learnontiktok","#educational","#science","#history","#mindblowing","#tipsandtricks","#explainer","#studytips","#howto","#learneveryday","#knowledgeispower","#curiosity","#studygram","#academics","#school","#college","#university","#teaching","#class"],
    "Comedy": ["#comedy","#funny","#humor","#laugh","#comedyreels","#funnyvideos","#comedytok","#jokes","#comedyvideo","#laughs","#funnymemes","#lol","#hilarious","#comedyskit","#funnymoments","#comedycentral","#comedyclips","#standupcomedy","#prank","#funnyclips","#comedylife","#funnyreel","#comedygold","#funnyguy","#funnygirl"],
    "Lifestyle": ["#lifestyle","#lifestyleblogger","#dayinmylife","#vlog","#contentcreator","#creator","#authentic","#lifestylevlog","#dailyvlog","#motivation","#selflove","#positivity","#mindset","#growthmindset","#lifetips","#wellbeing","#balance","#morningroutine","#selfcare","#habittracker","#personaldevelopment","#contentcreation","#reelsviral","#instareels","#viral"],
}


class HashtagGenerator:

    def __init__(self):
        self._api_key = os.getenv("GEMINI_API_KEY", "").strip()

    def generate(
        self,
        video_description: str,
        content_category: str,
        primary_activity: str = "",
    ) -> List[str]:

        if not self._api_key:
            return BANKS.get(content_category, BANKS["Lifestyle"])
        if not video_description or "unavailable" in video_description.lower():
            return BANKS.get(content_category, BANKS["Lifestyle"])

        act = f"Primary activity: {primary_activity}" if primary_activity and primary_activity != "Content creation" else ""

        prompt = f"""You are a social media hashtag strategist for Instagram Reels and TikTok.

CONTENT CATEGORY: {content_category}
{act}
VIDEO DESCRIPTION: {video_description}

Generate exactly 25 hashtags for this specific video.

Mix:
- 6 high-volume niche hashtags (millions of posts)
- 10 mid-tier specific hashtags (100K–1M posts)
- 5 long-tail hashtags (under 100K, very targeted)
- 4 trending hashtags relevant to this content

Rules:
- All hashtags must start with #
- No spaces within a hashtag
- Every hashtag must relate to the actual content ({content_category} / {primary_activity or content_category})
- Do NOT generate #lifestyle for {content_category} content
- Be specific to the exact activity, not just the general category

Return ONLY a JSON array of 25 strings (no explanation, no markdown):
["#tag1", "#tag2", ...]"""

        try:
            model = get_model()
            resp = model.generate_content(prompt)
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp.text.strip())
            tags = json.loads(text)
            validated = [t if t.startswith("#") else f"#{t}" for t in tags if t.strip()]
            return validated[:25] if validated else BANKS.get(content_category, BANKS["Lifestyle"])
        except Exception:
            return BANKS.get(content_category, BANKS["Lifestyle"])