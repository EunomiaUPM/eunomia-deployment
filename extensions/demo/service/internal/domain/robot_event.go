package domain

import (
	"encoding/json"

	"gorm.io/gorm"
)

type RobotEventModel struct {
	gorm.Model
	RobotID      uint   `json:"robot_id" binding:"required"`
	EventName    string `json:"event_name" binding:"required"`
	EventContent string `json:"event_content" binding:"required"`
}

type RobotEvent struct {
	gorm.Model
	RobotID      uint
	EventName    string
	EventContent interface{}
}

type RobotEventCreateRequest struct {
	RobotID      uint        `json:"robot_id" binding:"required"`
	EventName    string      `json:"event_name" binding:"required"`
	EventContent interface{} `json:"event_content" binding:"required"`
}

func (h *RobotEvent) MapToModel() (RobotEventModel, error) {
	contentBytes, err := json.Marshal(h.EventContent)
	if err != nil {
		return RobotEventModel{}, err
	}
	return RobotEventModel{
		RobotID:      h.RobotID,
		EventName:    h.EventName,
		EventContent: string(contentBytes),
	}, nil
}
