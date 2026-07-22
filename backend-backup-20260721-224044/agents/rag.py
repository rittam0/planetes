"""RAG pipeline for NASA document grounding."""
import os
from typing import List
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# Pre-loaded NASA documents (simplified for V1)
# In production, these would be fetched and embedded at build time
NASA_DOCS = [
    Document(
        page_content="""
Near-Earth Objects (NEOs) are comets and asteroids that have been nudged by the gravitational 
attraction of nearby planets into orbits that allow them to enter the Earth's neighborhood. 
Composed mostly of water ice with embedded dust particles, comets originally formed in the 
cold outer planetary system while most rocky asteroids formed in the warmer inner solar system 
between the orbits of Mars and Jupiter.

NASA's NEO Observations Program coordinates efforts to find, track, and characterize NEOs. 
As of 2024, over 35,000 NEOs have been discovered, with approximately 1,500 new objects 
found each year.
        """,
        metadata={"source": "NASA NEO Program Overview", "url": "https://www.nasa.gov/planetarydefense/overview"}
    ),
    Document(
        page_content="""
The Torino Scale is a method for categorizing the impact hazard associated with near-Earth 
objects (NEOs) such as asteroids and comets. It is intended as a communication tool for 
astronomers and the public to assess the seriousness of collision predictions.

The scale uses integer values from 0 to 10, where:
- 0: No hazard
- 1: Normal (routine discovery with no cause for public attention)
- 2-4: Meriting attention by astronomers
- 5-7: Threatening (close encounters meriting attention by public officials)
- 8-10: Certain collisions with localized to global consequences
        """,
        metadata={"source": "NASA Torino Scale", "url": "https://cneos.jpl.nasa.gov/sentry/torino_scale.html"}
    ),
    Document(
        page_content="""
Orbital debris, or "space junk," refers to defunct human-made objects in orbit around Earth. 
These include nonfunctional spacecraft, abandoned launch vehicle stages, mission-related debris, 
and fragmentation debris. NASA estimates there are over 500,000 pieces of debris larger than 
1 cm and over 100 million pieces larger than 1 mm.

Even small debris can damage spacecraft because of the high relative velocities in orbit. 
In Low Earth Orbit (LEO), objects travel at approximately 7-8 km/s. A 1 cm aluminum sphere 
at this speed has the kinetic energy equivalent to a 1 kg mass traveling at 120 km/h.
        """,
        metadata={"source": "NASA Orbital Debris Program", "url": "https://orbitaldebris.jsc.nasa.gov/"}
    ),
    Document(
        page_content="""
The SGP4 (Simplified General Perturbations 4) propagator is used to propagate satellite orbits. 
It was developed by NORAD and released in 1988. The model considers:
- Earth oblateness (J2, J3, J4 harmonics)
- Atmospheric drag
- Lunar and solar gravitational perturbations

SGP4 uses Two-Line Element (TLE) sets as input and produces position and velocity vectors 
in the True Equator Mean Equinox (TEME) coordinate system. Typical accuracy is within 
1-5 km for a few days after the epoch.
        """,
        metadata={"source": "NASA SGP4 Documentation", "url": "https://celestrak.org/columns/v04n03/"}
    ),
    Document(
        page_content="""
A conjunction is an event where two orbiting objects pass close to each other. Conjunction 
assessment involves computing the probability of collision between two objects. The process 
involves:

1. Propagating both objects to the time of closest approach (TCA)
2. Computing the miss distance between them
3. Estimating the collision probability based on position uncertainties
4. Comparing against a threshold to determine if action is needed

The US Space Force's 18th Space Defense Squadron provides conjunction data messages (CDMs) 
to satellite operators. CelesTrak's SOCRATES service provides public conjunction screening.
        """,
        metadata={"source": "NASA Conjunction Assessment", "url": "https://www.nasa.gov/conjunction-assessment"}
    ),
]

# Global vector store (initialized once)
_vector_store = None


def get_vector_store() -> Chroma:
    """Get or create the ChromaDB vector store."""
    global _vector_store
    if _vector_store is None:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        chunks = text_splitter.split_documents(NASA_DOCS)

        _vector_store = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory="./chroma_db"
        )
    return _vector_store


def retrieve_context(query: str, k: int = 3) -> List[str]:
    """Retrieve relevant NASA document chunks for a query."""
    store = get_vector_store()
    docs = store.similarity_search(query, k=k)
    return [d.page_content for d in docs]


def retrieve_with_sources(query: str, k: int = 3) -> List[dict]:
    """Retrieve chunks with source attribution."""
    store = get_vector_store()
    docs = store.similarity_search(query, k=k)
    return [
        {
            "content": d.page_content,
            "source": d.metadata.get("source", "Unknown"),
            "url": d.metadata.get("url", "")
        }
        for d in docs
    ]
