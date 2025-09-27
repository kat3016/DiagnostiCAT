"""
Test directo para debuggear las preguntas específicas
"""
import asyncio
import uuid
from datetime import datetime

# Importar las funciones necesarias
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.routers.medical_chat import handle_specific_questions, CONVERSATIONS, ConversationState

async def test_specific_questions():
    print("🧪 TEST DIRECTO: Preguntas específicas")
    print("="*50)
    
    # Crear conversación simulada
    conversation_id = str(uuid.uuid4())
    CONVERSATIONS[conversation_id] = {
        "state": ConversationState.SPECIFIC_QUESTIONS,
        "messages": [],
        "consent_given": True,
        "interview_data": {},
        "symptoms_collected": [
            "dolor: me duele el abdomen",
            "síntoma general: hace un dia", 
            "síntoma general: 8",
            "dolor: me duele al agacharme",
            "síntoma general: no",
            "síntoma general: no",
            "síntoma general: no"
        ],
        "questions_asked": 7,
        "min_questions": 7,
        "max_questions": 7,
        "specific_questions_asked": 0,  # Primera vez en preguntas específicas
        "specific_questions_max": 5,
        "specific_answers": [],
        "created_at": datetime.now()
    }
    
    try:
        print(f"📋 Conversación creada: {conversation_id}")
        print(f"🔍 Síntomas: {CONVERSATIONS[conversation_id]['symptoms_collected']}")
        
        # Llamar a la función de preguntas específicas
        response = await handle_specific_questions(conversation_id, "Empezar preguntas específicas")
        
        print(f"\n✅ RESPUESTA RECIBIDA:")
        print(f"Mensaje: {response.response[:200]}...")
        print(f"Agent Type: {response.agent_type}")
        print(f"Confidence: {response.confidence_score}")
        
        # Verificar el estado de la conversación después
        updated_conversation = CONVERSATIONS[conversation_id]
        print(f"\n📊 ESTADO DESPUÉS:")
        print(f"Questions Asked: {updated_conversation.get('specific_questions_asked', 'N/A')}")
        print(f"Questions List: {len(updated_conversation.get('specific_questions_list', []))} preguntas")
        if updated_conversation.get('specific_questions_list'):
            print("📝 PREGUNTAS GENERADAS:")
            for i, q in enumerate(updated_conversation['specific_questions_list'][:3], 1):
                print(f"  {i}. {q[:80]}...")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_specific_questions())