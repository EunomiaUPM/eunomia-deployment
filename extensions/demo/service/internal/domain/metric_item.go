package domain

import (
	"gorm.io/gorm"
)

type MetricItemType string

const (
	MetricKeyRobotEnergyUsage = "robot_energy_usage"
	MetricKeyRobotTemperature = "robot_temperature"
	MetricKeyRobotCycleTime   = "robot_cycle_time"
	MetricKeyRobotVibration   = "robot_vibration"
)

type MetricItemModel struct {
	gorm.Model     `gorm:"tableName:metric_items"`
	ID             uint           `gorm:"primaryKey;autoIncrement" json:"id"`
	ItemType       MetricItemType `gorm:"type:varchar(50);not null" json:"item_type"`
	LastValue      float64        `gorm:"not null" json:"last_value"`
	LastMeasuredAt string         `gorm:"type:date;not null" json:"last_measured_at"`
}

type MetricItem struct {
	ID             uint           `json:"id"`
	ItemType       MetricItemType `json:"item_type"`
	LastValue      float64        `json:"last_value"`
	LastMeasuredAt string         `json:"last_measured_at"`
	CurrentCount   int            `json:"current_count,omitempty"`
	IntervalCount  int            `json:"interval_count,omitempty"`
}

type MetricItemCreateRequest struct {
	ItemType MetricItemType `json:"item_type" binding:"required"`
}

type MetricItemUpdateRequest struct {
	LastValue float64 `json:"last_value" binding:"required"`
}

func (MetricItemModel) TableName() string {
	return "metric_items"
}

func (m *MetricItemModel) ToDomain(intervalCount int) MetricItem {
	return MetricItem{
		ID:             m.ID,
		ItemType:       m.ItemType,
		LastValue:      m.LastValue,
		LastMeasuredAt: m.LastMeasuredAt,
		CurrentCount:   0,
		IntervalCount:  intervalCount,
	}
}

func (m *MetricItem) ToModel() *MetricItemModel {
	return &MetricItemModel{
		ID:             m.ID,
		ItemType:       m.ItemType,
		LastValue:      m.LastValue,
		LastMeasuredAt: m.LastMeasuredAt,
	}
}
