import React, { useState } from 'react';
import styles from './chatbot.module.css';
import Langbot from './Langbot';
import axios from "axios";
import DataResults from "./DataResults";
import {
  TextInput, Text, ActionIcon, Stack, Loader, Box,
} from "@mantine/core";
import {IconSearch} from "@tabler/icons-react";
import ReflectionWrap from './ReflectionWrapper';


function Loading({visible, text}) {
  if (!visible) return;
  // eslint-disable-next-line consistent-return
  return (
    <Box h="40px" my={90}>
      <Stack>
        <Text ta="center">{text}</Text>
        <Loader variant="bars" mx="auto" />
      </Stack>
    </Box>
  );
}

const Chatbot = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);


  const handleSubmit = async (e) => {
    //e.preventDefault();
    if (!input.trim()) return;
    const userMessage = { text: input, user: true };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setLoading(true);

    ReflectionWrap(input, handleData, setMessages, setLoading);

    setInput('');
  };

  const handleData = async (url) => {
    setLoading(true);
    await axios
        .get(url)
        .then((resp) => {
            setMessages((prevMessages) => [...prevMessages,
               {text: <DataResults dataResponse={resp.data}/>, user: false}]);
            setLoading(false);
        })
        .catch((error) => {
            console.error("Error al realizar la consulta:", error);
            setLoading(false);
        });
};
  

  return (
    <div className={styles.chatbotContainer}>
      <div className={styles.chatbotMessages}>
        {messages.map((message, index) => (
          <div
            key={index}
            className={`${styles.message} ${message.user ? styles.userMessage : styles.aiMessage}`}
          >
            { message.text }
            {loading? <Loading visible={true}/>:<></>}
          </div>
        ))}
      </div>
      <TextInput
            className={styles.chatbotInputForm}
            placeholder='Enter your question...'
            value={input}
            size="xl"
            onKeyDown={(e) => {
                if (e.key === "Enter") {handleSubmit()}
            }}
            onChange={(e) => setInput(e.target.value)}
            rightSection={(
                <ActionIcon onClick={handleSubmit} variant="filled" color="eoc-yellow" radius="xl">
                  <IconSearch size="1rem" />
                </ActionIcon>
                )}
        />
    </div>
  );
};
export default Chatbot;