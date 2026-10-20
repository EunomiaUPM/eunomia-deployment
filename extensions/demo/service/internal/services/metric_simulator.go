package services

import (
	"context"
	"eunomia-demo-factory/internal/domain"
	"eunomia-demo-factory/internal/repo"
	"log"
	"math/rand"
	"sync"
	"time"
)

type MetricSimulatorService struct {
	state                string
	interval             time.Duration
	Items                []domain.MetricItem
	MetricItemRepository *repo.MetricItemRepository
	NotificationService  *NotificationService
	mu                   sync.RWMutex
}

func NewMetricSimulatorService(metricItemRepo *repo.MetricItemRepository, notificationsService *NotificationService) *MetricSimulatorService {
	return &MetricSimulatorService{
		state:                "stopped",
		interval:             3 * time.Second,
		Items:                []domain.MetricItem{},
		MetricItemRepository: metricItemRepo,
		NotificationService:  notificationsService,
	}
}

func (service *MetricSimulatorService) RegisterMetricItem(metricItem *domain.MetricItemCreateRequest) error {
	newMetricItem, _ := service.MetricItemRepository.CreateMetricItem(context.Background(), metricItem)
	service.mu.Lock()
	service.Items = append(service.Items, newMetricItem)
	service.mu.Unlock()
	return nil
}

func (service *MetricSimulatorService) Start(ctx context.Context) error {
	service.mu.Lock()
	if service.state == "running" {
		service.mu.Unlock()
		return nil
	}
	service.state = "running"
	service.mu.Unlock()

	ticker := time.NewTicker(service.interval)
	defer ticker.Stop()
	for {
		select {
		case <-ticker.C:
			service.mu.RLock()
			itemsToProcess := make([]domain.MetricItem, len(service.Items))
			copy(itemsToProcess, service.Items)
			service.mu.RUnlock()
			updatedItems := make([]domain.MetricItem, len(itemsToProcess))

			for i, item := range itemsToProcess {
				value := rand.Float64() * 100.0
				metric, err := service.MetricItemRepository.UpdateMetricItem(ctx, item.ID, &domain.MetricItemUpdateRequest{
					LastValue: value,
				})
				service.NotificationService.NotifyMetricUpdate(metric)
				if err != nil {
					log.Printf("failed to update metric item ID %d: %v", item.ID, err)
					updatedItems[i] = item
				} else {
					log.Printf("updated metric item ID %d: new value %.2f", metric.ID, metric.LastValue)
					updatedItems[i] = metric
				}
			}
			service.mu.Lock()
			service.Items = updatedItems
			service.mu.Unlock()
		case <-ctx.Done():
			service.mu.Lock()
			service.state = "stopped"
			service.mu.Unlock()
			log.Println("stopping simulator")
			return nil
		}
	}
}

func (service *MetricSimulatorService) Stop() error {
	if service.state == "stopped" {
		return nil
	}
	service.state = "stopped"
	return nil
}
