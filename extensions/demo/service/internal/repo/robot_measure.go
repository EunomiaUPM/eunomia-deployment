package repo

import (
	"context"
	"eunomia-demo-factory/internal/domain"

	"gorm.io/gorm"
)

type RobotMeasureRepository struct {
	DB *gorm.DB
}

func (repo *RobotMeasureRepository) GetRobotMeasuresByRobotID(ctx context.Context, d uint) ([]domain.RobotMeasure, error) {
	var measures []domain.RobotMeasure
	err := repo.DB.WithContext(ctx).Where("robot_id = ?", d).Find(&measures).Error
	return measures, err
}

func (repo *RobotMeasureRepository) TableName() string {
	return "robot_measures"
}

func (repo *RobotMeasureRepository) GetAllRobotMeasures(ctx context.Context) ([]domain.RobotMeasure, error) {
	var measures []domain.RobotMeasure
	err := repo.DB.WithContext(ctx).Find(&measures).Error
	return measures, err
}

func (repo *RobotMeasureRepository) CreateRobotMeasure(ctx context.Context, newMeasure *domain.RobotMeasureCreateRequest) (domain.RobotMeasure, error) {
	measure := domain.RobotMeasure{
		RobotID:          newMeasure.RobotID,
		Year:             newMeasure.Year,
		Cycles:           newMeasure.Cycles,
		UptimeHours:      newMeasure.UptimeHours,
		DowntimeHours:    newMeasure.DowntimeHours,
		EnergyKwh:        newMeasure.EnergyKwh,
		PartsProduced:    newMeasure.PartsProduced,
		DefectRate:       newMeasure.DefectRate,
		Oee:              newMeasure.Oee,
		MtbfHours:        newMeasure.MtbfHours,
		MaintenanceCount: newMeasure.MaintenanceCount,
		AvgTemperatureC:  newMeasure.AvgTemperatureC,
	}
	err := repo.DB.WithContext(ctx).Create(&measure).Error
	return measure, err
}

func (repo *RobotMeasureRepository) GetRobotMeasureByID(ctx context.Context, id uint) (domain.RobotMeasure, error) {
	var measure domain.RobotMeasure
	err := repo.DB.WithContext(ctx).First(&measure, id).Error
	return measure, err
}

func (repo *RobotMeasureRepository) UpdateRobotMeasure(ctx context.Context, id uint, updatedMeasure *domain.RobotMeasureUpdateRequest) (domain.RobotMeasure, error) {
	var measure domain.RobotMeasure
	if err := repo.DB.WithContext(ctx).First(&measure, id).Error; err != nil {
		return measure, err
	}
	if updatedMeasure.Cycles != nil {
		measure.Cycles = *updatedMeasure.Cycles
	}
	if updatedMeasure.UptimeHours != nil {
		measure.UptimeHours = *updatedMeasure.UptimeHours
	}
	if updatedMeasure.DowntimeHours != nil {
		measure.DowntimeHours = *updatedMeasure.DowntimeHours
	}
	if updatedMeasure.EnergyKwh != nil {
		measure.EnergyKwh = *updatedMeasure.EnergyKwh
	}
	if updatedMeasure.PartsProduced != nil {
		measure.PartsProduced = *updatedMeasure.PartsProduced
	}
	if updatedMeasure.DefectRate != nil {
		measure.DefectRate = *updatedMeasure.DefectRate
	}
	if updatedMeasure.Oee != nil {
		measure.Oee = *updatedMeasure.Oee
	}
	if updatedMeasure.MtbfHours != nil {
		measure.MtbfHours = *updatedMeasure.MtbfHours
	}
	if updatedMeasure.MaintenanceCount != nil {
		measure.MaintenanceCount = *updatedMeasure.MaintenanceCount
	}
	if updatedMeasure.AvgTemperatureC != nil {
		measure.AvgTemperatureC = *updatedMeasure.AvgTemperatureC
	}
	err := repo.DB.WithContext(ctx).Save(&measure).Error
	return measure, err
}

func (repo *RobotMeasureRepository) DeleteRobotMeasure(ctx context.Context, id uint) error {
	return repo.DB.WithContext(ctx).Delete(&domain.RobotMeasure{}, id).Error
}
