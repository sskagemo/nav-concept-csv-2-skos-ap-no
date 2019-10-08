# Todo: Finne miljø for å kjøre dette som en tjeneste, f.eks. Google App Engine
# Todo: Fjerne de siste http://jira ... -referansene
# Todo: Se flere todo-s i koden under
# Todo: Legge inn kjøring av validering med SHACL opp mot BegrepShape.ttl når graphen er ferdig
# Todo: Basere språk-tag på hva som er angitt i språkversjon pr begrep -- nå er alle tekstfelt tagget som @nb

# importer de relevante modulene
from rdflib import Namespace, Graph, BNode, URIRef, Literal
from rdflib.namespace import RDF, RDFS, SKOS, DCTERMS, XSD
import csv
import re # regular expressions


# filnavn
begrepsfil='begreper010919.csv' # opprinnelige csv-fila fra
begrepsfil_renset = "begreper_renset.csv" # fjernet JIRA-referanser. Fortsatt 10 referanser til http://jira ...
katalogfil='katalog.ttl' # beskrivelse av selve katalogen, brukes direkte
resultatfil = 'output.ttl' # den ferdige SKOS-AP-NO-fila
publisher = 'https://data.brreg.no/enhetsregisteret/api/enheter/889640782' # URI for Nav

# URI-en til begrepskatalogen. Må matche det som står i katalog.ttl
begrepskatalog_uri = 'https://www.nav.no/begrepskatalog'

# Etablere Namespace som ikke finnes i rdflib allerede
SKOSNO = Namespace('http://difi.no/skosno#')
XKOS = Namespace('http://rdf-vocabulary.ddialliance.org/xkos#')
SKOSXL = Namespace('http://www.w3.org/2008/05/skos-xl#')
SCHEMA = Namespace('http://schema.org/')
VCARD = Namespace('http://www.w3.org/2006/vcard/ns#')
DCAT = Namespace('http://www.w3.org/ns/dcat#')


# mappe kolonnetitlene  i begrepsfil med riktig vokabular
# NB! Må stå i samme rekkefølge som i CSV-fila!
kolonnetitler = {
    'ID': DCTERMS.identifier,
    'Term': SKOSXL.prefLabel,
    'Begrepsforklaring': SKOS.scopeNote,
    'Definisjon': SKOSNO.Definisjon, # definisjon er en del av skosno:Betydningsbeskrivelse
    'Språkversjoner': 'language',
    'Beskrivelsestype': DCTERMS.type, # kommentar til/type kilde, usikker på om dette er riktig
    'Alternative termer': SKOSXL.altLabel,
    'Kilde': RDFS.label, # kilde knyttes til betydningsbeskrivelse via dct:source [rdfs:label "blabla"]
    'Frarådde termer': SKOSXL.hiddenLabel,
    'Eksempel': SKOS.example,
}


# Etablerer grafen, og binder noen prefiks med tanke på output
graph = Graph()

graph.bind('skosxl', 'http://www.w3.org/2008/05/skos-xl#')
graph.bind('skos', 'http://www.w3.org/2004/02/skos/core#')
graph.bind('skosno', 'http://difi.no/skosno#')


# Funksjon som mottar en dict med innholdet i hver linje i csv-fila og kolonnetitlene som keys, og legger til begrep
def addConcept(subject, concept: dict) ->None:
    for i in concept:
        if concept[i] == "":
            pass
        elif (i == 'Term' or i == 'Alternative termer' or i == 'Frarådde termer'):
            t = BNode()
            graph.add((subject, kolonnetitler[i], t))
            graph.add((t, RDF.type, SKOSXL.Label))
            graph.add((t, SKOSXL.literalForm, Literal(concept[i], lang='nb')))
        elif i == "Definisjon":
            t1 = BNode()
            t2 = BNode()
            graph.add((subject, SKOSNO.betydningsbeskrivelse, t1))
            graph.add((t1, SKOS.scopeNote, Literal(concept['Begrepsforklaring'], lang='nb')))
            graph.add((t1, RDF.type, SKOSNO.Definisjon))
            graph.add((t1, RDFS.label, Literal(concept[i], lang='nb')))
            graph.add((t1, DCTERMS.type, Literal(concept['Beskrivelsestype'], lang='nb')))
            graph.add((t1, DCTERMS.source, t2))
            graph.add((t2, RDFS.label, Literal(concept['Kilde'], lang='nb')))
        elif i == 'ID':
            subject_uri = 'https://nav.no/begrep/' + str(concept[i])
            graph.add((subject, DCTERMS.identifier, Literal(subject_uri)))
        elif i == 'Kilde': # håndtert som del av definisjon
            pass
        elif i == 'Begrepsforklaring': # håndtert som del av definisjon
            pass
        elif i == 'Beskrivelsestype': # håndtert som del av definisjon
            pass
        elif i == 'Språkversjoner': # legges til fortløpende for alle relevante elementer
            pass
        else:
            graph.add((subject, kolonnetitler[i], Literal(concept[i], lang='nb')))
    return None


# Åpner den opprinnelige fila og renser for referanser til JIRA
# TODO Sjekk valg av encoding - stemmer det for filtypen vi får fra Nav?
with open (begrepsfil, mode='r', encoding='windows-1252') as infile:
    with open(begrepsfil_renset, mode='w', encoding='utf-8') as outfile:
        line = infile.readline()
        while line:
            line = re.sub('\|BEGREP-.{0,5}\]', "", str(line)) # regex funnet vha https://regex101.com/
            line = re.sub('\[', '', str(line)) # litt sårbar, i tilfelle '[' er brukt et sted i teksten
            outfile.write(line)
            line = infile.readline()





# Åpne katalogfil, parse og legge til graph
graph.parse(katalogfil, format='turtle')

# Åpne begrepsfil for lesing, traversere linjene, kalle addConcept med et nytt subjekt og dict
with open(begrepsfil_renset, encoding='utf-8') as csv_file:
    csv_reader = csv.DictReader(csv_file, delimiter=';', fieldnames=list(kolonnetitler.keys())) # Hver linje blir en dict med kolonnetitlene som keys

    # TODO: Kvalitet: Burde gjøre en test på om det er match mellom innholdet i første linje i csv og kolonnetitler.keys()
    # I tilfelle CSV-fila har fått ny layout kan det advares om ved å teste her og avbryte.
    line = next(csv_reader) # Første linje er kolonnetitler, hopper over den


    for line in csv_reader:
        print(line) # debug
        subject_uri = 'https://nav.no/begrep/' + str(line["ID"])
        subject = URIRef(subject_uri) # lager et nytt RDF-subjekt

        # Legger begrepet i form av RDF-subjektet inn som medlem i katalogen:
        graph.add((URIRef(begrepskatalog_uri), SKOS.member, subject))

        # Legger inn verdiene som ikke er del av CSV-fila, dvs type, publisher og id.
        # TODO: Mangler også "modified" men det finnes ikke i csv-fila
        graph.add((subject, RDF.type, SKOS.Concept))
        graph.add((subject, DCTERMS.publisher, URIRef(publisher)))

        addConcept(subject, line) # Bruker addConcept for de verdiene som finnes i CSV-fila


# Her bør det legges inn validering med pyshacl og BegrepShape.ttl, ref https://github.com/RDFLib/pySHACL
# TODO: Fjern begrep som ikke har definisjon. Finner alle konsepter og trekker fra de som _har_ definisjon

# Returnerer alle subjekt av typen skos:Concept som _ikke_ har skosno:betydningsbeskrivelse
qres = graph.query(
    """
    SELECT ?s
    {
        ?s a skos:Concept
        MINUS { ?s skosno:betydningsbeskrivelse ?b }
    }
    """
)

print(qres)

# går gjennom alle subjektene fra spørringen over, og fjerner først evt blanke noder knyttet til dem, deretter dem selv
for i in qres:
    for s, p, o in graph.triples((i[0], None, None)):
        if type(o) == BNode:
            graph.remove((o, None, None))

    graph.remove((i[0], None, None))


# Skrive ut RDF til *.ttl eller *.jsonld
print("Skriver ut resultatet")
graph.serialize(format='turtle', destination='output.ttl')
