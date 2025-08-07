import asyncio
import logging
from datetime import datetime

from pydantic_ai import Agent
from pydantic_ai.agent import AgentRunResult
from pydantic_ai.exceptions import ModelHTTPError
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from tenacity import (
    retry,
    wait_random_exponential,
    stop_after_attempt,
    before_sleep_log,
)

from models import Group, Message
from utils.chat_text import chat2text
from whatsapp import WhatsAppClient, SendMessageRequest

logger = logging.getLogger(__name__)


@retry(
    wait=wait_random_exponential(min=1, max=30),
    stop=stop_after_attempt(6),
    before_sleep=before_sleep_log(logger, logging.DEBUG),
    reraise=True,
)
async def summarize(group_name: str, messages: list[Message], chat_model=None) -> AgentRunResult[str]:
    # Note: This function doesn't have access to settings, so we use a default
    # This should be updated to receive settings for consistency
    if chat_model is None:
        from pydantic_ai.models.openai import OpenAIModel
        chat_model = OpenAIModel("gpt-4o")
    
    agent = Agent(
        model=chat_model,
        system_prompt=f"""Write a quick summary of what happened in the chat group since the last summary.
        
        LANGUAGE REQUIREMENTS (ABSOLUTELY CRITICAL):
        - You MUST respond in the EXACT same language as the chat messages below
        - If the chat messages are in Hebrew, respond ONLY in Hebrew
        - If the chat messages are in English, respond ONLY in English
        - If the chat messages are in Arabic, respond ONLY in Arabic
        - If messages are mixed languages, use the DOMINANT language of the messages
        - NEVER translate or change the language - maintain the original language at all costs
        - DO NOT default to English, Spanish, or any other language unless that's the actual language of the messages
        - Look at the actual language used in the messages and mirror it exactly
        
        CONTENT REQUIREMENTS:
        - Start by stating this is a quick summary of what happened in "{group_name}" group recently
        - Use a casual conversational writing style matching the group's tone
        - Keep it short and sweet
        - Tag users when mentioning them (e.g., @972536150150)
        - Focus on the main topics and interactions that happened
        """,
        output_type=str,
    )

    return await agent.run(chat2text(messages))


async def summarize_and_send_to_group(session, whatsapp: WhatsAppClient, group: Group):
    resp = await session.exec(
        select(Message)
        .where(Message.group_jid == group.group_jid)
        .where(Message.timestamp >= group.last_summary_sync)
        .where(Message.sender_jid != (await whatsapp.get_my_jid()).normalize_str())
        .order_by(desc(Message.timestamp))
    )
    messages: list[Message] = list(resp.all())

    if len(messages) < 15:
        logging.info("Not enough messages to summarize in group %s", group.group_name)
        return

    try:
        response = await summarize(group.group_name or "group", messages)
    except ModelHTTPError as e:
        if "content_filter" in str(e.body).lower() or "responsibleaipolicyviolation" in str(e.body).lower():
            logging.warning("Content filtered during automatic summarization for group %s", group.group_name)
            logging.debug("Content filter details: %s", e.body)
            return  # Skip this group's summary
        else:
            logging.error("Model HTTP error summarizing group %s: %s", group.group_name, e)
            return
    except Exception as e:
        logging.error("Error summarizing group %s: %s", group.group_name, e)
        return

    try:
        await whatsapp.send_message(
            SendMessageRequest(phone=group.group_jid, message=response.output)
        )

        # Send the summary to the community groups
        community_groups = await group.get_related_community_groups(session)
        for cg in community_groups:
            await whatsapp.send_message(
                SendMessageRequest(phone=cg.group_jid, message=response.output)
            )

    except Exception as e:
        logging.error("Error sending message to group %s: %s", group.group_name, e)

    finally:
        # Update the group with the new last_summary_sync
        group.last_summary_sync = datetime.now()
        session.add(group)
        await session.commit()


async def summarize_and_send_to_groups(session: AsyncSession, whatsapp: WhatsAppClient):
    groups = await session.exec(select(Group).where(Group.managed == True))  # noqa: E712 https://stackoverflow.com/a/18998106
    tasks = [
        summarize_and_send_to_group(session, whatsapp, group)
        for group in list(groups.all())
    ]
    errs = await asyncio.gather(*tasks, return_exceptions=True)
    for e in errs:
        if isinstance(e, BaseException):
            logging.error("Error syncing group: %s", e)
