package domain

import (
	"gorm.io/gorm"
)

// RobotMeasure is one year of production figures for a robot.
type RobotMeasure struct {
	gorm.Model
	RobotID          uint    `json:"robot_id"`
	Year             int     `json:"year"`
	Cycles           int     `json:"cycles"`
	UptimeHours      float64 `json:"uptimeHours"`
	DowntimeHours    float64 `json:"downtimeHours"`
	EnergyKwh        float64 `json:"energyKwh"`
	PartsProduced    int     `json:"partsProduced"`
	DefectRate       float64 `json:"defectRate"`
	Oee              float64 `json:"oee"`
	MtbfHours        float64 `json:"mtbfHours"`
	MaintenanceCount int     `json:"maintenanceCount"`
	AvgTemperatureC  float64 `json:"avgTemperatureC"`
}

type RobotMeasureCreateRequest struct {
	RobotID          uint    `json:"robot_id" binding:"required" faker:"boundary_start=1, boundary_end=50"`
	Year             int     `json:"year" binding:"required" faker:"boundary_start=2023, boundary_end=2027"`
	Cycles           int     `json:"cycles" binding:"required" faker:"boundary_start=250000, boundary_end=1800000"`
	UptimeHours      float64 `json:"uptimeHours" binding:"required" faker:"boundary_start=6200, boundary_end=8400"`
	DowntimeHours    float64 `json:"downtimeHours" binding:"required" faker:"boundary_start=120, boundary_end=900"`
	EnergyKwh        float64 `json:"energyKwh" binding:"required" faker:"boundary_start=8000, boundary_end=42000"`
	PartsProduced    int     `json:"partsProduced" binding:"required" faker:"boundary_start=200000, boundary_end=1500000"`
	DefectRate       float64 `json:"defectRate" binding:"required" faker:"boundary_start=0.002, boundary_end=0.035"`
	Oee              float64 `json:"oee" binding:"required" faker:"boundary_start=0.62, boundary_end=0.91"`
	MtbfHours        float64 `json:"mtbfHours" binding:"required" faker:"boundary_start=900, boundary_end=6500"`
	MaintenanceCount int     `json:"maintenanceCount" binding:"required" faker:"boundary_start=2, boundary_end=24"`
	AvgTemperatureC  float64 `json:"avgTemperatureC" binding:"required" faker:"boundary_start=31.5, boundary_end=58.0"`
}

type RobotMeasureUpdateRequest struct {
	Cycles           *int     `json:"cycles"`
	UptimeHours      *float64 `json:"uptimeHours"`
	DowntimeHours    *float64 `json:"downtimeHours"`
	EnergyKwh        *float64 `json:"energyKwh"`
	PartsProduced    *int     `json:"partsProduced"`
	DefectRate       *float64 `json:"defectRate"`
	Oee              *float64 `json:"oee"`
	MtbfHours        *float64 `json:"mtbfHours"`
	MaintenanceCount *int     `json:"maintenanceCount"`
	AvgTemperatureC  *float64 `json:"avgTemperatureC"`
}
