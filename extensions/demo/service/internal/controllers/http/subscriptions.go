package http

import (
	"eunomia-demo-factory/internal/domain"
	"eunomia-demo-factory/internal/services"

	"strconv"

	"github.com/gin-gonic/gin"
)

type SubscriptionsRouter struct {
	SubscriptionService *services.SubscriptionService
}

func (r *SubscriptionsRouter) Create(router *gin.Engine) {
	subscriptionsGroup := router.Group("/subscriptions")
	subscriptionsGroup.POST("/subscribe", r.subscribe)
	subscriptionsGroup.POST("/unsubscribe/:id", r.unsubscribe)
}

func (r *SubscriptionsRouter) subscribe(c *gin.Context) {
	var newSubscription domain.SubscriptionCreateRequest
	if err := c.ShouldBindJSON(&newSubscription); err != nil {
		c.JSON(400, gin.H{"error": err.Error()})
		return
	}
	sub, err := r.SubscriptionService.CreateSubscription(c.Request.Context(), &newSubscription)
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}
	c.JSON(201, gin.H{
		"message": "Subscribed successfully",
		"data":    sub,
	})
}

func (r *SubscriptionsRouter) unsubscribe(c *gin.Context) {
	id := c.Param("id")
	uid, err := strconv.ParseUint(id, 10, 32)
	if err != nil {
		c.JSON(400, gin.H{"error": "Invalid robot ID"})
		return
	}
	err = r.SubscriptionService.DeleteSubscription(c.Request.Context(), uint(uid))
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}
	c.JSON(200, gin.H{"message": "Unsubscribed successfully"})
}
