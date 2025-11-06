package handlers

import (
    "github.com/gin-gonic/gin"
    "net/http"
)

type User struct {
    ID   int    `json:"id"`
    Name string `json:"name"`
}

func GetUser(c *gin.Context) {
    user := User{ID: 1, Name: "John Doe"}
    c.JSON(http.StatusOK, user)
}
