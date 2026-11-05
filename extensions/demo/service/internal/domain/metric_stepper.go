package domain

type Stepper interface {
	DoStep() error
}
