package com.example.demo;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
public class Test1Controller {

    private Logger logger = LoggerFactory.getLogger("TestController");

    @RequestMapping("/test")
    public void test(){
        logger.info("test 성공");
    }

    @RequestMapping("/chatting")
    public void chatting(){
        logger.info("chatting 성공");
    }
}
