package domain

import (
	"gorm.io/gorm"
)

type Subscription struct {
	gorm.Model
	URL       string `json:"url"`
	EventType string `json:"event_type"`
}

type SubscriptionCreateRequest struct {
	URL       string `json:"url" binding:"required"`
	EventType string `json:"event_type" binding:"required"`
}
