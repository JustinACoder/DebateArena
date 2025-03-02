import os
import json
from django.db import IntegrityError
from debate.models import Debate
from tqdm import tqdm


def populate_debates(debate_list_file):
    with open(debate_list_file) as f:
        json_data = json.load(f)

    for i, debate_categories in enumerate(json_data):
        category = debate_categories['category']
        debate_subjects = debate_categories['debate_subjects']
        print(f'Populating debates for category: {category} ({i + 1}/{len(json_data)})')
        for debate_object in tqdm(debate_subjects):
            title = debate_object['subject']
            description = debate_object['description']

            try:
                # Create the debate
                # Note: we cannot use bulk because we need the save method to generate the slug and update the search vector
                # Note: there is probably a better way to do this, but this is a simple and enough for now
                Debate.objects.create(title=title, description=description)
            except IntegrityError:
                print(f"Debate with title '{title}' already exists. Skipping...")


def run():
    debate_list_file = os.path.join(os.path.dirname(__file__), 'debate_list.json')
    populate_debates(debate_list_file)
