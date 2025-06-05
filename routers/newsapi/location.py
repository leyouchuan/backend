import spacy
from geopy.geocoders import Nominatim

nlp = spacy.load("en_core_web_sm")
geolocator = Nominatim(user_agent="geoapiExercises")

def extract_locations(news_titles):
    locations = []
    for title in news_titles:
        doc = nlp(title)
        for ent in doc.ents:
            if ent.label_ == "GPE":  # GPE - Geo-Political Entity
                location = geolocator.geocode(ent.text)
                if location:
                    locations.append({
                        'name': ent.text,
                        'lat': location.latitude,
                        'lon': location.longitude
                    })
    return locations