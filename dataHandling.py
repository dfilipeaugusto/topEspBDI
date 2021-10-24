import pandas as pd
from rdflib import Dataset, URIRef, Literal, Namespace, Graph
from rdflib.namespace import FOAF, RDF

# Leitura do conjunto de dados original
df_vax = pd.read_stata('KK_vaccines.dta')

# Tratamento dos dados
def race_category(x):
    races = [x[f'race_{i}'] for i in range(1,7)]
    count = races.count(0)
    if count == 5:
        for race in races:
            if race!=0:
                return race
    else: return 'Other'

race = df_vax[['ResponseId'] + [f'race_{i}' for i in range(1,7)]].drop_duplicates(subset=('ResponseId'))
race['final_race'] = race.apply(lambda x : race_category(x), axis=1)
race.set_index('ResponseId', inplace=True)
race = race[['final_race']]
race.reset_index(inplace=True)

info = df_vax.drop_duplicates(subset=('ResponseId'))
info = info[['ResponseId', 'age', 'gender', 'party_lean']]

vaxord = df_vax.groupby('ResponseId').agg({'vaxord': 'mean'}).reset_index()

df_final = info.merge(race, on='ResponseId', how='left').merge(vaxord, on='ResponseId', how='left')
df_final.age = df_final.age.astype(int)

# Triplificação do conjunto de dados
g = Graph()

g.bind("ex", Namespace("http://example.com/participant/"))
g.bind("w3id", Namespace("https://w3id.org/survey-ontology#"))
g.bind("db-owl", Namespace("https://dbpedia.org/ontology/"))

class_participant = g.resource("https://w3id.org/survey-ontology#Participant")
prop_participantID = URIRef("https://w3id.org/survey-ontology#participantId")
prop_hasValue = URIRef("https://w3id.org/survey-ontology#hasValue")
prop_ethnicity = URIRef("https://dbpedia.org/ontology/ethnicity")

res_race = dict()
for race in df_final.final_race.unique():
    res_race[race] = g.resource(race.replace(" ", ""))
    res_race[race].add(RDF.type, URIRef("https://dbpedia.org/ontology/EthnicGroup"))
    
    
for row in df_final.values:
    responseId, age, gender, party, race, vaxord = row[0], row[1], row[2], row[3], row[4], row[5]
    person = g.resource(f"http://example.com/participant/{responseId}")
    person.add(RDF.type, class_participant)
    
    person.add(FOAF.age, Literal(age))
    person.add(FOAF.gender, Literal(gender))
    person.add(FOAF.topic_interest, Literal(party))
    
    person.add(prop_participantID, Literal(responseId))
    person.add(prop_hasValue, Literal(round(vaxord, 1)))
    person.add(prop_ethnicity, res_race[race])


# Exportação do arquivo em Turtle
with open("covid_vax.ttl", "w") as file1:
    file1.write(g.serialize(format="turtle"))