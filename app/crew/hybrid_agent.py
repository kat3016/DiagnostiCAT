"""
Agente híbrido que puede usar NVIDIA o OpenAI según disponibilidad
"""

from langchain_openai import ChatOpenAI
from app.core.config import settings
import os

def test_nvidia_availability():
    """Prueba si NVIDIA API está disponible"""
    
    if not settings.NVIDIA_API_KEY:
        return False, "No API key configurada"
    
    try:
        # Probar con un modelo simple
        llm = ChatOpenAI(
            model="nvidia/llama-3.1-nemotron-70b-instruct",
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=0.1,
            timeout=30
        )
        
        # Prueba simple
        response = llm.invoke("Hello, respond with 'OK' if you can read this.")
        return True, f"NVIDIA funcionando: {response.content}"
        
    except Exception as e:
        return False, f"Error NVIDIA: {str(e)}"

def create_hybrid_agent():
    """Crea agente que funciona con NVIDIA o OpenAI"""
    
    # Probar NVIDIA primero
    nvidia_works, nvidia_msg = test_nvidia_availability()
    print(f"🧪 Test NVIDIA: {nvidia_msg}")
    
    if nvidia_works:
        print("✅ Usando NVIDIA API")
        return ChatOpenAI(
            model="nvidia/llama-3.1-nemotron-70b-instruct",
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=0.7,
            timeout=60
        ), "nvidia"
    
    # Fallback a OpenAI si está configurado
    elif settings.OPENAI_API_KEY:
        print("⚡ Fallback a OpenAI API")
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.7,
            timeout=60
        ), "openai"
    
    else:
        raise Exception("Ni NVIDIA ni OpenAI están configurados correctamente")

def generate_questions_hybrid(interview_data: str, already_covered: str = "") -> dict:
    """Generates questions using the best available agent.

    already_covered: newline-delimited list of topics already answered in the
    general interview.  The LLM is instructed not to repeat these topics.
    """

    try:
        llm, provider = create_hybrid_agent()

        already_covered_section = ""
        if already_covered:
            already_covered_section = f"""
TOPICS ALREADY COLLECTED — DO NOT ask about any of these again:
{already_covered}

"""

        prompt = f"""You are a specialist physician in differential diagnosis. Analyze this medical interview and generate exactly 3 preliminary hypotheses and exactly 5 specific questions.

PATIENT INTERVIEW DATA:
{interview_data}
{already_covered_section}
The 5 specific questions MUST:
- Address ONLY details not already covered in the topics above
- Help differentiate between the top 3 differential diagnoses
- Explore red flags or alarm symptoms relevant to the chief complaint
- Ask about specific characteristics (quality, radiation, pattern) that distinguish conditions
- NEVER repeat onset timing, numeric intensity rating, basic medication list, or the main complaint description

Respond using EXACTLY this format (keep these exact section headers):

PRELIMINARY HYPOTHESES:
1. [First preliminary hypothesis - describe a possible condition without being definitive]
2. [Second preliminary hypothesis]
3. [Third preliminary hypothesis]

SPECIFIC QUESTIONS FOR CLASSIFICATION MODEL:
1. [First specific question to clarify the clinical picture]?
2. [Second specific question]?
3. [Third specific question]?
4. [Fourth specific question]?
5. [Fifth specific question]?

IMPORTANT RULES:
- Write ALL content in English only
- Every hypothesis must describe a possible condition without constituting a definitive diagnosis
- Every question must end with a question mark (?)
- Questions must be clinically relevant and specific to the patient's symptoms
- Do NOT add explanations or commentary outside the required format
"""

        print(f"🤖 Generating questions with {provider.upper()}...")
        response = llm.invoke(prompt)

        print(f"✅ Questions generated successfully by {provider.upper()}")

        return {
            "success": True,
            "content": response.content,
            "provider": provider,
            "model": "nvidia/llama-3.1-nemotron-70b-instruct" if provider == "nvidia" else settings.OPENAI_MODEL
        }

    except Exception as e:
        print(f"❌ Error in hybrid agent: {e}")
        return {
            "success": False,
            "error": str(e),
            "content": None
        }