# Import necessary libraries
import time
import re
import csv
import os
import openai
from sentence_splitter import SentenceSplitter

# Initialize the sentence splitter for English language
sentence_splitter = SentenceSplitter("en")

# Initialize the OpenAI API key and organization ID (please uncomment and set the actual values)
#openai.api_key = "YOUR_API_KEY"
#openai.organization_id = "YOUR_ORGANIZATION_ID"

# Function to query the AskAI API and return a modified response
def AskAI(question, persona):
    try:
        # Check if persona is provided
        if persona:
            response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": persona},
                {"role": "user", "content": question}
            ]
            )
        else:
            response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": question}
            ]
            )
        # Extract the initial response from the API
        initial_response = response["choices"][0]["message"]["content"]
        # Modify the response by removing initial sentences and second occurrences
        modified_response = remove_initial_sentence(initial_response)
        modified_response = remove_second_occurrence(modified_response)
        # Wait for 5 seconds before the next request to prevent rate limit errors
        time.sleep(5)
        return modified_response
    except openai.error.RateLimitError as e:
        # Handle rate limit errors by waiting and retrying
        print(e)
        time.sleep(60)
        AskAI(question, persona)
    except openai.error.APIError as e2:
        # Handle other API errors by waiting and retrying
        print(e2)
        time.sleep(20)
        AskAI(question, persona)

# Function to remove second occurrence of sentences
def remove_second_occurrence(text):
    sentence_dict = {}
    sentences = sentence_splitter.split(text)
    result = []
    for sentence in sentences:
        sentence = remove_leading_words(sentence)
        if sentence in sentence_dict:
            sentence_dict[sentence] += 1
        else:
            sentence_dict[sentence] = 1

        if sentence_dict[sentence] < 2:
            result.append(sentence.strip())

    return ' '.join(result)

# Function to remove leading words from the response
def remove_leading_words(text):
    # Regex to find ". " at the start of the text.
    regex_dot = re.compile(r"^\.\s", re.IGNORECASE)
  
    # Regex to find "However, " at the start of the text.
    regex_however = re.compile(r"^However,\s", re.IGNORECASE)
  
    # Remove the matched strings.
    text = regex_dot.sub("", text)
    text = regex_however.sub("", text)
  
    # Capitalize the first character of the remaining string.
    text = text[:1].upper() + text[1:]
  
    return text

# Function to remove the initial sentence if it's a specific ChatGPT phrase
def remove_initial_sentence(response):
    first_sentence = response.split(".")[0]
    if first_sentence.startswith("As an AI language model"):
        response = response.replace(first_sentence, "")
    return response

# Class definition for EgoState
class EgoState:
    _data = None  # Class-level data variable

    # Class method to read data from the CSV file
    @classmethod
    def read_csv(cls):
        with open("ego_states.csv", "r") as f:
            reader = csv.reader(f)
            data = {row[0]: row for row in reader}
        cls._data = data

    # Initializer for the EgoState class
    def __init__(self, id):
        if EgoState._data is None:
            self.read_csv()
            
        if id in EgoState._data:
            self.id = id
            self.behavioral_mode = EgoState._data[id][1]
            self.asks_questions_to = EgoState._data[id][2]
        else:
            raise ValueError(f"No ego state found with id {id}")

    # Representation function for the EgoState class
    def __repr__(self):
        return f"EgoState(id={self.id}, behavioral_mode={self.behavioral_mode}, asks_questions_to={self.asks_questions_to})"

    # Function to ask questions to other ego-states and collect responses
    def ask_other_ego_states(self, question): #Pass on question to other ego-states and get answers back.
      # Get the list of EgoState objects that the current EgoState object should ask questions to.
      asks_questions_to_list = self.asks_questions_to.split(",")
      print(self.id, " will ask ", self.asks_questions_to)
    
      # Create a list to store the responses from the other EgoState objects.
      responses = []
    
      # Loop over the list of EgoState objects that the current EgoState object asks questions to.
      for asks_questions_to_id in asks_questions_to_list:
        # Get the EgoState object with the specified ID.
        other_ego_state = EgoState(asks_questions_to_id)
    
        # Call the be_asked_question method on the other EgoState object.
        print("Asking", other_ego_state.id)
        response = other_ego_state.be_asked_question(other_ego_state.question_flavour())
            
        # Add the response to the list of responses.
        responses.append(response)
    
      # Return the list of responses.
      return responses

    # Function for an ego-state to be asked a question and to provide an answer
    def be_asked_question(self, question): #Receive a question and provide an answer  
        # If asks_questions_to is not populated, then find the answer ourselves.
        if not self.asks_questions_to:
          print(self.id, "has no-one else to ask, will find its own answer")
          own_answer = ''
          own_answer = self.find_answer(question)
          print('\n', self.id, " says ", own_answer, '\n')
          return own_answer          
      
        # Otherwise, ask the other ego states and then formulate our own answer.
        print(self.id, " will ask ", self.asks_questions_to)
        answers = []
        for asks_questions_to_id in self.asks_questions_to.split(","):
          other_ego_state = EgoState(asks_questions_to_id)
          answer = other_ego_state.be_asked_question(other_ego_state.question_flavour())
          answers.append(answer)

        # Formulate own answer based on the answers from the other ego states.
        print("Now ", self.id, " will formulate its own opinion based on these answers")
        answer = self.formulate_opinion(answers)
        print('\n', self.id, " says ", answer, '\n')
      
        return answer

    # Function to formulate an opinion based on answers from other ego-states
    def formulate_opinion(self, answers): 
        # Create a list to store the answers from the other ego states.
        answers_list = []
    
        # Loop over the answers.
        for answer in answers:
            # Add the answer to the list.
            answers_list.append(answer)

        print("Number of answers to reconcile:", len(answers_list))
        prompt = ''
        if len(answers_list)==1:
            persona = "You are " + self.behavioral_mode
            prompt = f"You were asked: {self.question_flavour()} You were presented an answer someone else formulated: {answers_list}. Formulate your own response to the question while taking into account the opinions of the other person."
        else:
            persona = "You are " + self.behavioral_mode
            prompt = f"You were asked: {self.question_flavour()} You were presented with answers provided by other people. One answered: {answers_list[0]}. The other one answered: {answers_list[1]}. Formulate your own response to the question, by synthesizing the provided answers, while adding a layer of your own understanding."            
        persona = "You are " + self.behavioral_mode
        return(AskAI(prompt, persona))
    
    # This function is for when the ego state needs to find an answer directly without consulting other ego states
    def find_answer(self, question): #Ask question to AskAI
        # Construct the persona for the specific ego state
        persona = "As a " + self.behavioral_mode
        
        # Ask the AI the question with the appropriate persona for context
        return (AskAI(self.question_flavour(), persona))        

    # This function determines the kind of question each ego state will ask based on its nature
    def question_flavour(self): #What is the right question for this ego state?
        # Depending on the nature (Parent, Adult, Child) of the ego state, adjust the focus of the question
        if self.id.split(".")[0] == 'Parent':
            return(parent_question)
        elif self.id.split(".")[0] == 'Adult':
            return(initial_question)
        else:
            return(child_question)  

###########################################################################################################################

# The main function to execute the code
def main():
    pass

if __name__ == "__main__":   
    # Read in the CSV data containing details about different ego states
    EgoState.read_csv()

    # Collect the initial question from the user
    initial_question = input("Please enter your initial question: ")
    print('Initial question: ', initial_question,'\n')
    
    # Translate the initial question into a form suitable for the Parent ego state
    parent_question = ''
    Parent = EgoState("Parent.Parent")
    temp_question = f"As a {Parent.behavioral_mode}, what does the problem - {initial_question} - mean to you? Only state the rephrased problem, do not give the answer to the question."
    parent_question = AskAI(temp_question, '')
    print('Parent ego state version of the question: ', parent_question,'\n')

    # Translate the initial question into a form suitable for the Child ego state
    child_question = ''
    Child = EgoState("Child.Child")
    temp_question = f"As a {Child.behavioral_mode}, what does the problem - {initial_question} - mean to you? Only state the rephrased problem, do not give the answer to the question."
    child_question = AskAI(temp_question, '')
    print('Child ego state version of the question: ', child_question,'\n')
    
    # Create an instance of the Adult ego state and ask it the question
    obj = EgoState("Adult.Adult")

    final_answer = obj.be_asked_question(initial_question)

