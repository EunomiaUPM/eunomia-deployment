package repo

import (
	"context"

	"eunomia-demo-factory/internal/domain"

	"gorm.io/gorm"
)

type SubscriptionRepository struct {
	DB *gorm.DB
}

func (repo *SubscriptionRepository) TableName() string {
	return "subscriptions"
}

func (repo *SubscriptionRepository) CreateSubscription(ctx context.Context, newSubscription *domain.SubscriptionCreateRequest) (domain.Subscription, error) {
	var existing domain.Subscription
	err := repo.DB.WithContext(ctx).Where("url = ? AND event_type = ?", newSubscription.URL, newSubscription.EventType).First(&existing).Error
	if err == nil {
		return domain.Subscription{}, gorm.ErrDuplicatedKey
	}
	if err != nil && err.Error() != gorm.ErrRecordNotFound.Error() {
		return domain.Subscription{}, err
	}
	subscription := domain.Subscription{
		URL:       newSubscription.URL,
		EventType: newSubscription.EventType,
	}
	err = repo.DB.WithContext(ctx).Create(&subscription).Error
	return subscription, err
}

func (repo *SubscriptionRepository) GetAllSubscriptions(ctx context.Context) ([]domain.Subscription, error) {
	var subscriptions []domain.Subscription
	err := repo.DB.WithContext(ctx).Find(&subscriptions).Where("deleted_at IS NOT NULL").Error
	return subscriptions, err
}

func (repo *SubscriptionRepository) GetSubscriptionByID(ctx context.Context, id uint) (domain.Subscription, error) {
	var subscription domain.Subscription
	err := repo.DB.WithContext(ctx).First(&subscription, id).Error
	return subscription, err
}

func (repo *SubscriptionRepository) DeleteSubscription(ctx context.Context, id uint) error {
	return repo.DB.WithContext(ctx).Delete(&domain.Subscription{}, id).Error
}
