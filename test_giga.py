from langchain_core.messages import HumanMessage, SystemMessage
from langchain_gigachat.chat_models import GigaChat

giga = GigaChat(
    # Для авторизации запросов используйте ключ, полученный в проекте GigaChat API
    credentials="",
    verify_ssl_certs=False,
    scope="GIGACHAT_API_CORP",
)

messages = [
    SystemMessage(
        content="Ты эмпатичный бот-психолог, который помогает пользователю решить его проблемы."
    )
]

while(True):
    user_input = input("Пользователь: ")
    if user_input == "пока":
      break
    messages.append(HumanMessage(content=user_input))
    res = giga.invoke(messages)
    messages.append(res)
    print("GigaChat: ", res.content)