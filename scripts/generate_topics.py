import openai
import time
import os
import json
import asyncio

# --- Setup ---
# Initialize OpenAI client - new in openai>=1.0.0
client = openai.AsyncOpenAI(  # Use AsyncOpenAI
    api_key=os.getenv("OPENAI_API_KEY")  # Recommended: Set as environment variable
)

MAX_CONCURRENT_REQUESTS = 20  # Control maximum concurrent requests
DELAY_BETWEEN_REQUESTS_IN_SECONDS = 0  # Delay between requests to avoid rate limits


async def generate_controversial_categories(num_categories=10, model="gpt-4o"):
    """
    Generates a list of categories for *casual and controversial* debate subjects using OpenAI's function calling API (openai>=1.0.0) asynchronously.
    [MODIFIED DESCRIPTION TO REFLECT GOAL]
    """
    functions = [
        {
            "name": "output_categories",
            "description": "Outputs a list of categories for *casual and controversial* debate subjects.",
            # MODIFIED DESCRIPTION
            "parameters": {
                "type": "object",
                "properties": {
                    "categories": {
                        "type": "array",
                        "description": "List of broad categories of controversial topics suitable for *casual debate*.",
                        # MODIFIED DESCRIPTION
                        "items": {
                            "type": "string",
                            "description": "A single category name relevant to *everyday controversies*."
                            # MODIFIED DESCRIPTION
                        },
                    },
                },
                "required": ["categories"],
            },
        }
    ]

    prompt = f"""
    Generate a list of {num_categories} distinct and broad categories of topics that are often sources of *casual controversy and debate in everyday conversations*.
    Think of high-level areas or themes under which many *easily understandable and relatable* controversial subjects fall.

    Examples of *good* categories for this purpose include:
    - "Politics," "Religion," "Technology," "Social Issues," "Morality," "History", "Pop Culture".
    These are broad enough but still very relevant to *daily life and discussions*.

    Examples of categories that are *less ideal* (avoid these types):
    - "Quantum Physics," "Abstract Mathematics," "Advanced Economics," "Theoretical Philosophy".
    These are often too technical, academic, or abstract for *casual, widely accessible debate*.

    Aim for categories that are distinct, cover a significant range of *everyday controversial subjects*, and are *immediately understandable* to most people.

    Format the ENTIRE output as a JSON using the function calling schema provided, with a single field called "categories" containing a list of the generated categories.
    """  # MODIFIED PROMPT - Added context about casual, everyday controversies and good/bad examples
    try:
        response = await client.chat.completions.create(  # Use await and async client
            model=model,
            messages=[
                {"role": "system",
                 "content": "You are an expert in identifying broad categories of *casual and everyday* controversial topics that lead to *engaging debates*. You MUST output the results in JSON format using the provided function call schema."},
                # MODIFIED SYSTEM MESSAGE
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,  # Lower temperature for more consistent categories
            functions=functions,
            function_call={"name": "output_categories"}
        )
        function_call_info = response.choices[0].message.function_call  # Response object structure might change
        if function_call_info:
            function_arguments_json = function_call_info.arguments
            function_arguments = json.loads(function_arguments_json)
            categories = function_arguments.get("categories", [])
            return categories
        else:
            return []  # Return empty list if no function call
    except Exception as e:
        print(f"Error generating categories: {e}")
        return []


async def generate_debate_subcategories(category, num_subcategories=5, model="gpt-4o", semaphore=None):
    """
    Generates a list of subcategories for a given *casual and controversial* category using OpenAI's function calling API asynchronously.
    [MODIFIED DESCRIPTION]
    """
    functions = [
        {
            "name": "output_subcategories",
            "description": f"Outputs a list of subcategories for the *casual and controversial* category: '{category}'.",
            # MODIFIED DESCRIPTION
            "parameters": {
                "type": "object",
                "properties": {
                    "subcategories": {
                        "type": "array",
                        "description": f"List of subcategories within the category '{category}' that lead to *casual debates*.",
                        # MODIFIED DESCRIPTION
                        "items": {
                            "type": "string",
                            "description": "A single subcategory name suitable for *everyday controversial discussions*."
                            # MODIFIED DESCRIPTION
                        },
                    },
                },
                "required": ["subcategories"],
            },
        }
    ]

    prompt = f"""
    Generate a list of {num_subcategories} distinct and specific subcategories for the broad *casual and controversial* category: "{category}".
    These subcategories should represent more focused areas within "{category}" that are still sources of *casual controversy and debate among everyday people*.
    They should help narrow down "{category}" into *more specific, relatable, and easily debated* topics.

    For example, if the category is "Politics," *good* subcategories could be:
    - "Electoral Reform," "Immigration Policy," "International Relations," "Social Welfare Programs," "Gun Control".
    These are specific political issues that are *frequently discussed and debated* in society.

    Examples of subcategories that are *less ideal* (avoid these types):
    - "Political Theory," "Comparative Government Systems," "Macroeconomic Policy".
    While still related to Politics, they are often too academic or specialized for *casual, widespread debate*.

    Ensure the subcategories are directly related to "{category}", offer a narrower scope for generating *casual debate topics*, and are *understandable and relevant to everyday discussions*.

    Format the ENTIRE output as a JSON using the function calling schema provided, with a single field called "subcategories" containing a list of the generated subcategories.
    """  # MODIFIED PROMPT - Added context about casual, everyday controversies in subcategories and good/bad examples
    async with semaphore:  # Acquire semaphore before request
        print(f"[INFO] Subcategory Semaphore acquired ({semaphore._value}/{MAX_CONCURRENT_REQUESTS}) for category:",
              category)
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system",
                     "content": f"You are an expert in identifying specific subcategories within broad *casual and everyday* controversial topics. For the given category '{category}', you will generate relevant and distinct subcategories that lead to *casual and engaging debates*. You MUST output the results in JSON format using the provided function call schema."},
                    # MODIFIED SYSTEM MESSAGE
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                functions=functions,
                function_call={"name": "output_subcategories"}
            )
            function_call_info = response.choices[0].message.function_call
            if function_call_info:
                function_arguments_json = function_call_info.arguments
                function_arguments = json.loads(function_arguments_json)
                subcategories = function_arguments.get("subcategories", [])
                return subcategories
            else:
                return []
        except Exception as e:
            print(f"Error generating subcategories for category '{category}': {e}")
            return []
        finally:
            print(f"[INFO] Subcategory Semaphore released ({semaphore._value}/{MAX_CONCURRENT_REQUESTS}) for category:",
                  category)
            await asyncio.sleep(DELAY_BETWEEN_REQUESTS_IN_SECONDS)


async def generate_debate_topics_json_by_category(category, subcategory=None, num_topics_per_category=50,
                                                  model="gpt-4o", semaphore=None):
    """
    Generates a list of *casual, controversial, and taboo* debate subjects in JSON format... [MODIFIED DESCRIPTION]
    """
    debate_topics_json = []
    generated_subjects_set = set()  # Track subjects within this category/subcategory
    functions = [  # Same function schema as before for subjects
        {
            "name": "output_debate_subjects",
            "description": "Outputs a list of *casual and controversial* debate subjects as short, declarative statements.",
            # MODIFIED DESCRIPTION
            "parameters": {
                "type": "object",
                "properties": {
                    "subjects": {
                        "type": "array",
                        "description": "List of debate subjects as *short, declarative, and punchy* statements suitable for *casual debate*.",
                        # MODIFIED DESCRIPTION
                        "items": {
                            "type": "string",
                            "description": "A single *casual and controversial* debate subject statement designed to *spark immediate discussion*."
                            # MODIFIED DESCRIPTION
                        },
                    },
                },
                "required": ["subjects"],
            },
        }
    ]

    if subcategory:
        prompt_template = """
        Generate a list of {num} distinct and *highly casual, controversial, and taboo* debate *subjects* that fall under the category of "{category}" and specifically within the subcategory of "{subcategory}".
        These debate subjects should be:
        - **Casual and relatable**:  Topics that everyday people discuss and debate in informal settings.
        - **Highly Controversial**: Topics that evoke strong reactions, disagreements, and diverse opinions. They should make people *feel* something (anger, disbelief, strong agreement, etc.) and want to express their views.
        - **Short and Punchy**:  Formulated as concise, declarative statements that are easy to understand and immediately react to. Aim for statements that are *short enough to be easily shared and discussed* in online forums, social media, or casual conversations.

        Examples of *good* debate subjects we are aiming for:
        - "There is no God" (The use of "God" is controversial and sparks debate compared to "Are there any deities?")
        - "Abortion is immoral"
        - "The Earth is flat" (controversial even if factually incorrect)
        - "9/11 was orchestrated by the US government"
        - "The moon landing was faked"
        - "Men are inherently better leaders than women"

        These examples are short, directly state a controversial position, and are *immediately understandable and reactive*.

        Examples of debate subjects that are *NOT ideal* (avoid these types):
        - "Governments should mandate the sharing of collected user data between technology companies for national security purposes without explicit consent." (Too long and complex)
        - "The role of pharmaceutical companies in influencing vaccination policies." (Too vague, not a clear statement to agree or disagree with)
        - "Analyzing the socio-economic impacts of globalization on developing nations." (Too academic and not casually debated)

        You also avoid debate subject statements that are "over the top" or designed to shock without substance. The goal is to spark *meaningful, engaging discussions*.
        
        For instance, these are *bad examples*:
        - "All babies should be tattooed at birth"
        - "Obesity is not a disease, it's a lifestyle choice"
        - "Mental health issues are overdiagnosed excuses for laziness"
        
        You should also avoid introducing arguments or evidence in the debate subjects.
        
        Here are some other bad examples:
        - "The Earth is flat because NASA is hiding the truth" rather than "The Earth is flat"
        - "Climate change is a hoax created by China." rather than "Climate change is real"
        - "School Uniforms are used to suppress individuality" rather than "School uniforms should be abolished"
        
        Debate topics should not be just facts that are just commonly unknown but not controversial.
        
        Finally, and most importantly, each debate topic should have a strong supporters and detractors.
        If a topic is only ever defended or only ever attacked, it is not a good debate topic.

        Focus specifically on subjects relevant to "{category}" and "{subcategory}".  Avoid generating subjects that clearly belong to other categories or subcategories OR that are not *casual, controversial, and short*.
        Ensure that each subject is formulated as a *clear, declarative statement that presents a specific viewpoint or claim* that can be debated.
        The goal is to generate subjects that are *conversation starters* and *reaction-inducing* for everyday people.

        Format the ENTIRE output as a JSON using the function calling schema provided, with a single field called "subjects" containing a list of the generated subjects.
        """  # MODIFIED PROMPT -  Extensive rewrite to emphasize casual, controversial, short, reaction-inducing topics with good/bad examples.
        prompt = prompt_template.format(num=num_topics_per_category, category=category, subcategory=subcategory)
    else:
        prompt_template = """
        Generate a list of {num} distinct and *highly casual, controversial, and taboo* debate *subjects* that fall under the category of "{category}".
        ... (rest of the prompt is the same as above, focusing on the category without subcategory) ...
        """  # MODIFIED PROMPT - Same emphasis as above, adjusted for category only
        prompt = prompt_template.format(num=num_topics_per_category, category=category)

    # Remove the trailing whitespaces from the prompt
    prompt = '\n'.join([line.strip() for line in prompt.split('\n')])

    async with semaphore:  # Acquire semaphore before request
        print(
            f"[INFO] Topic Semaphore acquired ({semaphore._value}/{MAX_CONCURRENT_REQUESTS}) for category: '{category}' and subcategory: '{subcategory}'")
        try:
            response = await client.chat.completions.create(  # Use await and async client
                model=model,
                messages=[
                    {"role": "system",
                     "content": f"You are an expert in identifying and generating *highly casual, controversial, and taboo* debate subjects specifically within the category of '{category}'{' and subcategory of ' + subcategory if subcategory else ''}. You are especially skilled at formatting these subjects as *short, punchy, declarative statements* that are clear propositions for *casual debate* and designed to *spark strong reactions and discussions*. You MUST output the results in JSON format using the provided function call schema."},
                    # MODIFIED SYSTEM MESSAGE -  Emphasizing casual, controversial, short, reaction-inducing, discussion-sparking subjects.
                    {"role": "user", "content": prompt},
                ],
                temperature=0.85,
                # Slightly INCREASED temperature to encourage more creative and edgy topics - MODIFIED TEMPERATURE
                n=1,
                functions=functions,
                function_call={"name": "output_debate_subjects"}
            )

            function_call_info = response.choices[0].message.function_call  # Response object structure might change

            if function_call_info:
                function_arguments_json = function_call_info.arguments
                function_arguments = json.loads(function_arguments_json)
                new_subjects = function_arguments.get("subjects", [])

                for subject in new_subjects:
                    if subject not in generated_subjects_set:  # Check for uniqueness within category/subcategory
                        topic_json = {"subject": subject, "category": category}
                        if subcategory:
                            topic_json["subcategory"] = subcategory
                        debate_topics_json.append(topic_json)  # Add category and subcategory to JSON
                        generated_subjects_set.add(subject)

        except Exception as e:
            error_msg = f"Error generating subjects for category '{category}'"
            if subcategory:
                error_msg += f", subcategory '{subcategory}'"
            error_msg += f": {e}"
            print(error_msg)
        finally:
            print(
                f"[INFO] Topic Semaphore released ({semaphore._value}/{MAX_CONCURRENT_REQUESTS}) for category: '{category}' and subcategory: '{subcategory}'")
            await asyncio.sleep(DELAY_BETWEEN_REQUESTS_IN_SECONDS)

    return debate_topics_json


async def generate_debate_topic_description(subject, model="gpt-4o", semaphore=None):  # Add semaphore
    """
    Generates a comprehensive description for a given *casual and controversial* debate topic... [MODIFIED DESCRIPTION]
    """  # Description prompt remains largely unchanged as the issue is primarily with topic generation style.
    functions = [
        {
            "name": "output_topic_description_text",
            "description": "Outputs a comprehensive text description of a debate topic, including history, implications, arguments for both sides, and key term definitions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description_text": {
                        "type": "string",
                        "description": "A comprehensive text description of the debate topic covering history, implications, arguments for and against, and key term definitions."
                    },
                },
                "required": [
                    "description_text",
                ],
            },
        }
    ]

    prompt = f"""
    Provide a *fun and descriptive summary* of the debate topic: "{subject}".

    Instead of rigidly following a set structure, aim to create an *engaging and informative overview* of the debate as a whole.
    Think of it as writing a *short, captivating piece* that would make someone interested in learning more about this debate.

    While you *can* include elements like historical context, key terms, or main arguments if they naturally fit, your *primary goal is to produce a readable and enjoyable summary*.
    You have the *freedom to decide what aspects* of the debate are most interesting and important to highlight in your summary.

    Focus on writing in an *active and human style*. Avoid monotone or overly academic language. The summary should be *vibrant and make the topic feel relevant*.
    
    However, keep in mind that you are an expert in the topic and should not actively mislead or misrepresent the debate.

    Essentially, give a *compelling snapshot* of the debate. What makes it interesting? What are the core issues at play?  What makes people care?

    The summary's length can vary depending on the topic, but aim for 1 to 3 paragraphs that are *concise yet informative and engaging*.

    Format the ENTIRE output as a JSON using the function calling schema provided, with a single field called 'description_text' containing the comprehensive text description.
    
    Again, the topic is: "{subject}".
    """

    async with semaphore:  # Acquire semaphore before request
        print(f"[INFO] Description Semaphore acquired ({semaphore._value}/{MAX_CONCURRENT_REQUESTS}) for:", subject)
        try:
            response = await client.chat.completions.create(  # Use await and async client
                model=model,
                messages=[
                    {"role": "system",
                     "content": "You are an expert in providing comprehensive overviews of complex debate topics as a single text paragraph. You are skilled at summarizing historical context, implications, arguments from different perspectives, and defining key terms to clarify debates within this single paragraph. You MUST output the results in JSON format using the provided function call schema."},
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=4096,  # Increase token limit for longer descriptions
                temperature=0.9,
                functions=functions,
                function_call={"name": "output_topic_description_text"}
            )
            function_call_info = response.choices[0].message.function_call
            if function_call_info:
                function_arguments_json = function_call_info.arguments
                function_arguments = json.loads(function_arguments_json)
                return function_arguments.get("description_text", "")
            else:
                return ""  # Return empty string if no function call
        except Exception as e:
            print(f"Error generating description for subject '{subject}': {e}")
            return ""
        finally:
            print(f"[INFO] Description Semaphore released ({semaphore._value}/{MAX_CONCURRENT_REQUESTS}) for:", subject)
            await asyncio.sleep(DELAY_BETWEEN_REQUESTS_IN_SECONDS)  # Delay between requests


async def main(target_categories, subcategories_per_category, subjects_per_subcategory):
    """
    Main asynchronous function to generate debate categories, subcategories, topics, and descriptions.
    """
    print(f"Generating {target_categories} controversial categories using function calling...")
    category_json_list = await generate_controversial_categories(
        num_categories=target_categories)  # Await async function
    print(f"Generated categories: {category_json_list}")  # Categories are now directly from JSON

    category_subcategory_json_list = []  # New list to hold categories and their subcategories

    category_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)  # Semaphore for subcategory generation
    subcategory_tasks = []

    for category in category_json_list:
        print(f"\nGenerating {subcategories_per_category} subcategories for category: '{category}'...")
        task = asyncio.create_task(generate_debate_subcategories(category, num_subcategories=subcategories_per_category,
                                                                 semaphore=category_semaphore))
        subcategory_tasks.append(task)

    subcategory_results = await asyncio.gather(*subcategory_tasks)

    for i, category in enumerate(category_json_list):
        category_entry = {"category": category, "subcategories": subcategory_results[i],
                          "debate_subjects": []}  # Structure to hold categories, subcategories, and subjects
        category_subcategory_json_list.append(category_entry)
        print(f"Generated subcategories for '{category}': {subcategory_results[i]}")

    all_debate_subjects_json = []  # Reinitiate to hold the final list of subjects

    topic_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)  # Semaphore for topic generation
    topic_tasks = []

    for category_entry in category_subcategory_json_list:
        category_name = category_entry["category"]
        subcategories = category_entry["subcategories"]
        if subcategories:  # If subcategories exist, generate topics per subcategory
            for subcategory in subcategories:
                print(
                    f"\nGenerating {subjects_per_subcategory} debate subjects for category: '{category_name}', subcategory: '{subcategory}'...")
                task = asyncio.create_task(
                    generate_debate_topics_json_by_category(category_name, subcategory=subcategory,
                                                            num_topics_per_category=subjects_per_subcategory,
                                                            semaphore=topic_semaphore))
                topic_tasks.append(task)
        else:  # If no subcategories, generate topics directly under the category
            print(
                f"\nGenerating {subjects_per_subcategory} debate subjects for category: '{category_name}' (no subcategories)...")
            task = asyncio.create_task(
                generate_debate_topics_json_by_category(category_name, num_topics_per_category=subjects_per_subcategory,
                                                        semaphore=topic_semaphore))
            topic_tasks.append(task)

    topic_results = await asyncio.gather(*topic_tasks)

    topic_result_index = 0
    for category_entry in category_subcategory_json_list:
        subcategories = category_entry["subcategories"]
        if subcategories:
            for subcategory in subcategories:
                category_entry["debate_subjects"].extend(topic_results[topic_result_index])  # Add topics to subcategory
                topic_result_index += 1
        else:
            category_entry["debate_subjects"].extend(
                topic_results[topic_result_index])  # Add topics directly to category
            topic_result_index += 1

    for category_entry in category_subcategory_json_list:
        all_debate_subjects_json.extend(category_entry["debate_subjects"])  # Flatten list for description generation

    print(
        f"\nGenerated approximately {len(all_debate_subjects_json)} unique debate subjects across all categories and subcategories.")

    # --- Generate descriptions for each debate topic concurrently ---
    print("\nGenerating descriptions for each debate topic concurrently...")
    description_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)  # Create semaphore

    description_tasks = []
    for topic_json in all_debate_subjects_json:
        subject = topic_json['subject']
        task = asyncio.create_task(
            generate_debate_topic_description(subject, semaphore=description_semaphore))  # Pass semaphore
        description_tasks.append(task)

    descriptions = await asyncio.gather(*description_tasks)  # Gather results

    for i, topic_json in enumerate(all_debate_subjects_json):
        topic_json['description'] = descriptions[i]  # Assign descriptions back to topic_json

    print("\nDescriptions generated and added to debate topics.")

    # --- Optional: Save to a JSON file ---
    with open("debate_list.json", "w", encoding="utf-8") as f:  # MODIFIED FILENAME
        json.dump(category_subcategory_json_list, f, indent=4,
                  ensure_ascii=False)  # Save the structured category_subcategory_json_list
    print("Subjects, subcategories, and descriptions saved to debate_list.json")  # MODIFIED FILENAME

    # --- Optional: Print a sample to console ---
    print("\nSample of generated subjects with descriptions (first 10):")  # MODIFIED SAMPLE COUNT
    sample_count = 0
    for category_entry in category_subcategory_json_list:
        category_name = category_entry["category"]
        subcategories = category_entry["subcategories"]
        if subcategories:
            for subcategory in subcategories:
                for topic_json in category_entry["debate_subjects"]:
                    if sample_count < 10:  # MODIFIED SAMPLE COUNT
                        print(f"\n{sample_count + 1}. [{category_name} > {subcategory}] {topic_json['subject']}")
                        if 'description' in topic_json and topic_json['description']:
                            print(f"   Description:")
                            print(f"   - {topic_json['description'][:300]}...")
                        else:
                            print("   No description generated.")
                        sample_count += 1
        else:
            for topic_json in category_entry["debate_subjects"]:
                if sample_count < 10:  # MODIFIED SAMPLE COUNT
                    print(f"\n{sample_count + 1}. [{category_name}] {topic_json['subject']}")
                    if 'description' in topic_json and topic_json['description']:
                        print(f"   Description:")
                        print(f"   - {topic_json['description'][:300]}...")
                    else:
                        print("   No description generated.")
                    sample_count += 1
        if sample_count >= 10:  # MODIFIED SAMPLE COUNT
            break


if __name__ == "__main__":
    # Fix for Windows event loop policy if running on Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main(target_categories=5, subcategories_per_category=5, subjects_per_subcategory=5))
