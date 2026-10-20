package domain

import (
	"gorm.io/gorm"
)

type RobotModel struct {
	gorm.Model `gorm:"tableName:robots"`
	Name       string         `json:"name"`
	ModelName  string         `json:"model"`
	Line       string         `json:"line"`
	Measures   []RobotMeasure `json:"-" gorm:"foreignKey:RobotID"`
}

func (RobotModel) TableName() string {
	return "robots"
}

type Robot struct {
	Name      string         `json:"name"`
	ModelName string         `json:"model"`
	Line      string         `json:"line"`
	Measures  []RobotMeasure `json:"measures,omitempty"`
}

type RobotCreateRequest struct {
	Name      string `json:"name" binding:"required" faker:"oneof:Atlas,Bolt,Cobalt,Dynamo,Echo,Forge,Gizmo,Helix,Ion,Jett"`
	ModelName string `json:"model" binding:"required" faker:"oneof:KR-210 Quantec,IRB 6700,M-20iD/25,UR10e,GP25,LBR iiwa 14"`
	Line      string `json:"line" binding:"required" faker:"oneof:Line A,Line B,Line C,Line D,Line E"`
}

type RobotUpdateRequest struct {
	Name      *string `json:"name"`
	ModelName *string `json:"model"`
	Line      *string `json:"line"`
}
