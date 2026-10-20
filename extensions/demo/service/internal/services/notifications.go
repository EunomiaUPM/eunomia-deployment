package services

import (
	"bytes"
	"context"
	"encoding/json"
	"eunomia-demo-factory/internal/domain" // Asumo que este es el import correcto para tu repo
	"eunomia-demo-factory/internal/repo"
	"log"
	"net/http"
	"sync"
	"time" // <-- FIX: Importar 'time'
)

type NotificationService struct {
	subscriptionRepo *repo.SubscriptionRepository // Usar la interfaz
	httpClient       *http.Client
	jobChannel       chan domain.MetricItem
	httpJobChannel   chan httpJob
	workerPoolSize   int
}

type httpJob struct {
	Url     string
	Payload []byte
}

func NewNotificationService(subscriptionRepo *repo.SubscriptionRepository, workerPoolSize int) *NotificationService {
	return &NotificationService{
		subscriptionRepo: subscriptionRepo,
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
		jobChannel:     make(chan domain.MetricItem, 10),
		httpJobChannel: make(chan httpJob, 2000),
		workerPoolSize: workerPoolSize,
	}
}

func (n *NotificationService) Start(ctx context.Context, wg *sync.WaitGroup) {
	log.Println("Notification Service starting...")
	wg.Add(1 + n.workerPoolSize)
	go n.getSubscribersWorker(ctx, wg)
	for i := 0; i < n.workerPoolSize; i++ {
		go n.httpSenderWorker(ctx, wg, i+1)
	}
}

func (n *NotificationService) NotifyMetricUpdate(metricItem domain.MetricItem) {
	select {
	case n.jobChannel <- metricItem:
		log.Printf("Enqueued notification job for metric item ID %d", metricItem.ID)
	default:
		log.Printf("Notification job channel full, dropping notification for metric item ID %d", metricItem.ID)
	}
}

func (n *NotificationService) getSubscribersWorker(ctx context.Context, wg *sync.WaitGroup) {
	defer wg.Done()
	log.Println("getSubscribersWorker started")

	for {
		select {
		case <-ctx.Done():
			log.Println("getSubscribersWorker shutting down")
			return

		case metricItem := <-n.jobChannel:
			payload, err := json.Marshal(metricItem)
			if err != nil {
				log.Printf("failed to marshal metric item: %v", err)
				continue
			}
			subscribers, err := n.subscriptionRepo.GetAllSubscriptions(ctx)
			if err != nil {
				log.Printf("failed to get subscribers: %v", err)
				continue
			}
			if len(subscribers) == 0 {
				continue // No subscribers to notify
			}

			log.Printf("Fanning-out notification for metric %s to %d subscribers", metricItem.ItemType, len(subscribers))
			for _, sub := range subscribers {
				job := httpJob{
					Url:     sub.URL,
					Payload: payload,
				}
				select {
				case n.httpJobChannel <- job:
					// enqueued for httpSenderWorker
				case <-ctx.Done():
					log.Println("getSubscribersWorker shutting down, job not sent.")
					return
				}
			}
		}
	}
	// --------------------------------------------------------
}

func (n *NotificationService) httpSenderWorker(ctx context.Context, wg *sync.WaitGroup, workerID int) {
	defer wg.Done()
	log.Printf("httpSenderWorker %d started", workerID)

	for {
		select {
		case job := <-n.httpJobChannel:
			log.Printf("[Worker %d] Sending notification to %s", workerID, job.Url)

			req, err := http.NewRequestWithContext(ctx, "POST", job.Url, bytes.NewBuffer(job.Payload))
			if err != nil {
				log.Printf("[Worker %d] ERROR creating request for %s: %v", workerID, job.Url, err)
				continue
			}
			req.Header.Set("Content-Type", "application/json")

			resp, err := n.httpClient.Do(req)
			if err != nil {
				log.Printf("[Worker %d] ERROR sending POST to %s: %v", workerID, job.Url, err)
				continue
			}

			if resp.StatusCode < 200 || resp.StatusCode >= 300 {
				log.Printf("[Worker %d] FAILED notification to %s, status: %s", workerID, job.Url, resp.Status)
			}
			resp.Body.Close()

		case <-ctx.Done():
			log.Printf("httpSenderWorker %d shutting down.", workerID)
			return
		}
	}
}
