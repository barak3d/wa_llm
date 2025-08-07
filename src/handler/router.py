import logging
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession
from openai import AsyncAzureOpenAI

from handler.knowledge_base_answers import KnowledgeBaseAnswers
from models import Message
from whatsapp.jid import parse_jid
from utils.chat_text import chat2text
from whatsapp import WhatsAppClient
from .base_handler import BaseHandler

# Creating an object
logger = logging.getLogger(__name__)


class IntentEnum(str, Enum):
    summarize = "summarize"
    ask_question = "ask_question"
    about = "about"
    other = "other"


class Intent(BaseModel):
    intent: IntentEnum = Field(
        description="""The intent of the message.
- summarize: Summarize TODAY's chat messages, or catch up on the chat messages FROM TODAY ONLY. This will trigger the summarization of the chat messages. This is only relevant for queries about TODDAY chat. A query across a broader timespan is classified as ask_question
- ask_question: Ask a question or learn from the collective knowledge of the group. This will trigger the knowledge base to answer the question.
- about: Learn about me(bot) and my capabilities. This will trigger the about section.
- other:  something else. This will trigger the default response."""
    )


class Router(BaseHandler):
    def __init__(
        self,
        session: AsyncSession,
        whatsapp: WhatsAppClient,
        embedding_client: AsyncAzureOpenAI,
        settings,
    ):
        self.ask_knowledge_base = KnowledgeBaseAnswers(
            session, whatsapp, embedding_client, settings
        )
        super().__init__(session, whatsapp, embedding_client, settings)

    async def __call__(self, message: Message):
        if message.text is None:
            logger.warning(f"Received message with no text from {message.sender_jid}")
            return
            
        route = await self._route(message.text)
        match route:
            case IntentEnum.summarize:
                await self.summarize(message)
            case IntentEnum.ask_question:
                await self.ask_knowledge_base(message)
            case IntentEnum.about:
                await self.about(message)
            case IntentEnum.other:
                await self.default_response(message)

    async def _route(self, message: str) -> IntentEnum:
        agent = Agent(
            model=self.settings.get_chat_model(),
            system_prompt="What is the intent of the message? What does the user want us to help with?",
            output_type=Intent,
        )

        try:
            result = await agent.run(message)
            return result.output.intent
        except ModelHTTPError as e:
            if "content_filter" in str(e.body).lower() or "responsibleaipolicyviolation" in str(e.body).lower():
                logger.warning(f"Content filtered for message routing. Message preview: {message[:50]}...")
                logger.debug(f"Content filter details: {e.body}")
                # Default to 'other' for filtered content - safe fallback
                return IntentEnum.other
            else:
                logger.error(f"Model HTTP error in routing: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error in message routing: {e}")
            # Default to 'other' for any other errors to keep bot functioning
            return IntentEnum.other

    async def summarize(self, message: Message):
        time_24_hours_ago = datetime.now() - timedelta(hours=24)
        stmt = (
            select(Message)
            .where(Message.chat_jid == message.chat_jid)
            .where(Message.timestamp >= time_24_hours_ago)
            .order_by(desc(Message.timestamp))
            .limit(30)
        )
        res = await self.session.exec(stmt)
        messages: list[Message] = list(res.all())

        if not messages:
            await self.send_message(
                message.chat_jid,
                "No messages found from today to summarize.",
                message.message_id,
            )
            return

        agent = Agent(
            model=self.settings.get_chat_model(),
            system_prompt="""Summarize the following group chat messages in a few words.
            
            LANGUAGE REQUIREMENTS (CRITICAL):
            - You MUST respond in the EXACT same language as the chat messages
            - If messages are in Hebrew, respond ONLY in Hebrew
            - If messages are in English, respond ONLY in English  
            - If messages are mixed languages, use the DOMINANT language of the messages
            - NEVER translate or change the language - maintain the original language at all costs
            - DO NOT default to English or Spanish unless that's the actual language of the messages
            
            CONTENT REQUIREMENTS:
            - You MUST state that this is a summary of TODAY's messages
            - Always personalize the summary to the user's request
            - Keep it short and conversational
            - Tag users when mentioning them (e.g., @972536150150)
            - Even if the user asked for a summary of a different time period, state that you can only summarize today's messages
            """,
            output_type=str,
        )

        try:
            response = await agent.run(
                f"@{parse_jid(message.sender_jid).user}: {message.text}\n\n # History:\n {chat2text(messages)}"
            )
            await self.send_message(
                message.chat_jid,
                response.output,
                message.message_id,
            )
        except ModelHTTPError as e:
            if "content_filter" in str(e.body).lower() or "responsibleaipolicyviolation" in str(e.body).lower():
                logger.warning(f"Content filtered during summarization for chat {message.chat_jid}")
                logger.debug(f"Content filter details: {e.body}")
                await self.send_message(
                    message.chat_jid,
                    "I'm sorry, but I can't summarize today's messages due to content policy restrictions. Some messages may contain content that can't be processed.",
                    message.message_id,
                )
            else:
                logger.error(f"Model HTTP error in summarization: {e}")
                await self.send_message(
                    message.chat_jid,
                    "I encountered an error while trying to summarize today's messages. Please try again later.",
                    message.message_id,
                )
        except Exception as e:
            logger.error(f"Unexpected error in summarization: {e}")
            await self.send_message(
                message.chat_jid,
                "I encountered an unexpected error while summarizing. Please try again later.",
                message.message_id,
            )

    async def about(self, message):
        await self.send_message(
            message.chat_jid,
            "I'm an open-source bot - \nI can help you catch up on the chat messages and answer questions based on the group's knowledge.",
            message.message_id,
        )

    async def default_response(self, message):
        await self.send_message(
            message.chat_jid,
            "I'm sorry, but I dont think this is something I can help with right now 😅.\n I can help catch up on the chat messages or answer questions based on the group's knowledge.",
            message.message_id,
        )
