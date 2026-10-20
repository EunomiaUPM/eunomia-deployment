package domain

type EventEmmiter interface {
	EmitMetricEvent(metricKey MetricItemType, value float64) error
}
