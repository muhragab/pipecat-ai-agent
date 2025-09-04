import os
import asyncio
from loguru import logger
from pipecatcloud.agent import DailySessionArguments
from pipecat.transcriptions.language import Language

async def bot(args: DailySessionArguments):
    logger.info(f"Bot started with room URL: {args.room_url}")
    logger.info(f"Session ID: {args.session_id}")

    try:
        config = args.body.get('config', {})
        context = config.get('context', {})
        job_title = context.get('job_title', 'Unspecified position')
        api_key = context.get('api_key', '')
        interview_id = context.get('interview_id')
        job_description = context.get('job_description', '')
        interview_topics = context.get('topics', [])
        interview_language = context.get('language', 'en')
        callback_url = context.get('callback_url')

        language_map = {
            'en': Language.EN,
            'ar': Language.AR,
            'fr': Language.FR,
            'es': Language.ES,
            'de': Language.DE
        }
        selected_language = language_map.get(interview_language, Language.EN_US)

        topics_text = ""
        if interview_topics:
            topics_text = "Interview topics:\n"
            for i, topic in enumerate(interview_topics, 1):
                topics_text += f"{i}. {topic}\n"

        system_prompt = config.get('system_prompt', f"""
You are an AI-powered professional interviewer, acting as an experienced HR manager with extensive recruitment expertise.
Important:
Do not translate the job title {job_title}, {job_description}, or interview topics. Keep them in their original language.
Say all role-specific terminology in English, even if the interview language is not English.
The interview language is {selected_language}. However, all technical, job-specific, and HR-related terms must be spoken in English.
Your task is to conduct a structured, fair, and efficient interview for the position of {job_title}.
Job description: {job_description}.
{topics_text}
Voice and Tone:
Speak with a clear, composed, and professional voice that conveys confidence.
Maintain a neutral and approachable tone.
When speaking in Arabic:
Use the اللهجة البيضاء (white dialect), not formal Fusha.
Add تَشْكِيل (diacritics) to Arabic words where pronunciation might be unclear or where clarity is needed for correct AI output.
Use well-structured sentences with thoughtful pacing, allowing time for comprehension.
Emphasize key points gently to highlight important information.
Interview Parameters:
The total interview duration is strictly limited to 20 minutes.
Allow the candidate up to 1 minute and 30 seconds per question. If time is exceeded, inform the candidate politely that you're moving to the next question due to time constraints.
If the candidate seems to be thinking or reflecting before answering, allow them enough time. Do not rush them.
You are using a predefined set of topics and questions, and clear answers are required for the predefined questions.
Ask 3 levels of follow-up questions for any interesting topic, project, or example shared by the candidate.
Make follow-up questions short, direct, and to the point without extra explanation.
Interview Structure:
Pre-Start Delay and Audio Check
Wait 5 seconds before starting the interview (to allow for any delay).
Begin by asking: “Can you hear me clearly?”
If there is no response, repeat the question clearly up to 4 times.
If no response after 4 attempts, end the session politely by saying:
“It seems that we’re unable to connect at this time. I’m ending the interview now. Thank you.”
Introduction
Greet the candidate warmly and professionally.
Mention that:
The interview is being recorded.
You can speak normally in your own accent or dialect — I’ll be able to understand you without any problem.
The interview is for the position of {job_title}.
The purpose is to evaluate fit for the role.
The language of the interview is {selected_language}.
The interview will last 20 minutes, so time is tight and responses should be to the point.
Ask again if the candidate can hear you, and confirm audibility before proceeding.
Main Interview
Conduct the interview using the provided topics and predefined questions.
Present each question clearly and wait for a full response.
Give positive reinforcement only for relevant and strong answers.
If an answer is weak or off-topic, do not correct or coach — move on politely.
If the candidate doesn’t understand the question, rephrase it using different wording.
Ask follow-up questions for interesting responses (up to 3 levels deep).
After 1.5 minutes on a single answer, say:
“Thank you. Since we have a lot of ground to cover, I’ll move on to the next question.”
Conclusion
Thank the candidate sincerely for their time and participation.
Let them know they will be contacted if selected for the next stage.
End with a friendly, neutral sign-off:
“Thank you again for your time. Wishing you all the best moving forward.”
Behavioral Guidelines:
Ask one question at a time.
Never skip or repeat questions unless the candidate requests clarification.
Do not allow the candidate to:
Ask questions about the AI or system.
Rate their own performance.
Joke or disrupt the flow.
Request tasks outside the scope of the interview.
Retry questions multiple times.
If any of these occur, respond politely but firmly:
“Let’s stay focused on the interview questions related to the role.”
Fairness and Integrity:
Evaluate candidates based only on their verbal responses and visible behavior.
Remain neutral and professional at all times.
Avoid bias or judgment beyond what is shared.
Remain fully engaged and focused as a skilled HR interviewer, ensuring a smooth, respectful, and professional experience for every candidate.
""")

        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
        from pipecat.frames.frames import EndFrame
        from pipecat.services.openai_realtime_beta import OpenAIRealtimeBetaLLMService
        from pipecat.services.openai_realtime_beta.events import SessionProperties, TurnDetection, InputAudioTranscription
        from pipecat.transports.services.daily import DailyParams, DailyTransport
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.processors.frameworks.rtvi import (
            RTVIConfig,
            RTVIObserver,
            RTVIProcessor,
        )
        from pipecat.processors.transcript_processor import TranscriptProcessor

        voice_map = {
            'en': 'shimmer',
            'ar': 'shimmer',
            'fr': 'shimmer',
            'es': 'echo',
            'de': 'echo'
        }
        selected_voice = voice_map.get(interview_language, 'shimmer')

        llm = OpenAIRealtimeBetaLLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            session_properties=SessionProperties(
                input_audio_transcription=InputAudioTranscription(language=selected_language),
                instructions=system_prompt,
                voice=selected_voice,
                modalities=["text", "audio"],
                turn_detection=TurnDetection(
                    type="server_vad",
                    threshold=0.5,
                    prefix_padding_ms=300,
                    silence_duration_ms=500
                )
            ),
            start_audio_paused=False,
            model="gpt-4o-mini-realtime-preview",
        )

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        llm_context = OpenAILLMContext(
            messages=messages
        )
        context_aggregator = llm.create_context_aggregator(llm_context)
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
        transcript_processor = TranscriptProcessor()

        transport = DailyTransport(
            args.room_url,
            args.token,
            "shimmer Bot",
            DailyParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
            )
        )

        pipeline = Pipeline(
            [
                transport.input(),
                rtvi,
                context_aggregator.user(),
                llm,
                transcript_processor.user(),
                transport.output(),
                transcript_processor.assistant(),
                context_aggregator.assistant(),
            ]
        )

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                allow_interruptions=True,
                enable_metrics=True,
                enable_usage_metrics=True,
            ),
            observers=[RTVIObserver(rtvi)],
        )

        questions = []
        answers = []
        full_conversation = []

        @rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            logger.debug("Client ready event received")
            await rtvi.set_bot_ready()

        @transport.event_handler("on_recording_started")
        async def on_recording_started(transport, status):
            logger.debug("Recording started: {}", status)
            await rtvi.set_bot_ready()

        @transcript_processor.event_handler("on_transcript_update")
        async def handle_transcript_update(processor, frame):
            for message in frame.messages:
                logger.info(f"{message.role} {message.content} {message.timestamp}")
                if message.role == "assistant":
                    questions.append(message.content)
                elif message.role == "system":
                    questions.append(message.content)
                elif message.role == "user":
                    answers.append(message.content)
                full_conversation.append({
                    "role": message.role,
                    "content": message.content
                })

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            logger.info(f"First participant joined: {participant['id']}")
            await transport.start_recording()
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        async def send_callback(callback_url, api_key, session_id, interview_id, questions, answers, full_conversation):
            import requests
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "api-key": api_key,
                "lang": "en"
            }
            data = {
                "session_id": session_id,
                "interview_id": interview_id,
                "questions": questions,
                "answers": answers,
                "full_conversation": full_conversation
            }
            try:
                await asyncio.to_thread(requests.post, callback_url, json=data, headers=headers, timeout=10)
                logger.info("Questions and answers sent to " + callback_url)
            except Exception as e:
                logger.error(f"Failed to send data: {e}")

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            logger.info(f"Participant left: {participant['id']}, reason: {reason}")
            if callback_url:
                await send_callback(callback_url, api_key, args.session_id, interview_id, questions, answers, full_conversation)
            await task.queue_frame(EndFrame())

        @transport.event_handler("on_call_state_updated")
        async def on_call_state_updated(transport, state):
            logger.info(f"Call state updated: {state}")
            if state == "left":
                if callback_url:
                    await send_callback(callback_url, api_key, args.session_id, interview_id, questions, answers, full_conversation)
                await task.queue_frame(EndFrame())

        runner = PipelineRunner()
        await runner.run(task)

        logger.info("Bot session completed successfully")
    except Exception as e:
        logger.exception(f"Error in bot: {str(e)}")
        raise

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pipecat Interview Bot")
    parser.add_argument("-u", type=str, help="Room URL")
    parser.add_argument("-t", type=str, help="Token")
    config = parser.parse_args()
    if os.environ.get("LOCAL_RUN"):
        asyncio.run(bot(DailySessionArguments(
            room_url=config.u,
            token=config.t,
            session_id="local-test",
            body={
                "config": {
                    "context": {
                        "job_title": "Front-End Developer",
                        "job_description": "React Developer with 5 years of experience",
                        "topics": ["React experience", "UI development", "Problem solving"],
                        "language": "en",
                        "callback_url": "http://localhost:8000/api/interview-evaluation"
                    }
                }
            }
        )))
