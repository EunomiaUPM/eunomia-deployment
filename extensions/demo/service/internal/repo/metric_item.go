package repo

import (
	"context"
	"eunomia-demo-factory/internal/domain"
	"time"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type MetricItemRepository struct {
	DB *gorm.DB
}

func (repo *MetricItemRepository) GetAllMetricItems(ctx context.Context) ([]domain.MetricItem, error) {
	var metricItems []domain.MetricItem
	err := repo.DB.WithContext(ctx).Find(&metricItems).Error
	return metricItems, err
}

func (repo *MetricItemRepository) CreateMetricItem(ctx context.Context, newMetricItem *domain.MetricItemCreateRequest) (domain.MetricItem, error) {
	metricModel := domain.MetricItemModel{
		ItemType:       newMetricItem.ItemType,
		LastValue:      0.0,
		LastMeasuredAt: time.Now().Format(time.RFC3339),
	}
	err := repo.DB.WithContext(ctx).Create(&metricModel).Error
	return metricModel.ToDomain(0), err
}

func (repo *MetricItemRepository) GetMetricItemByID(ctx context.Context, id uint) (domain.MetricItem, error) {
	var metricItem domain.MetricItem
	err := repo.DB.WithContext(ctx).First(&metricItem).Error
	return metricItem, err
}

func (repo *MetricItemRepository) UpdateMetricItem(ctx context.Context, id uint, updatedMetricItem *domain.MetricItemUpdateRequest) (domain.MetricItem, error) {
	updateData := map[string]interface{}{
		"last_value":       updatedMetricItem.LastValue,
		"last_measured_at": gorm.Expr("CURRENT_TIMESTAMP"), // Usar gorm.Expr es correcto
	}
	var updatedItem domain.MetricItemModel
	result := repo.DB.WithContext(ctx).Model(&updatedItem).Clauses(clause.Returning{}).Where("id = ?", id).Updates(updateData)
	returnItem := updatedItem.ToDomain(0)
	if result.Error != nil {
		return domain.MetricItem{}, result.Error
	}
	return returnItem, nil
}

func (repo *MetricItemRepository) DeleteMetricItem(ctx context.Context, id uint) error {
	return nil
}
