export const TOUR_EVENTS = {
  start: "bioqure:tour-start",
  welcome: "bioqure:tour-welcome",
  docs: "bioqure:tour-docs",
  support: "bioqure:tour-support",
};

const emit = (name) => window.dispatchEvent(new CustomEvent(name));

/** Start the step-by-step tour from anywhere in the app. */
export const startProductTour = () => emit(TOUR_EVENTS.start);
/** Show the first-visit welcome popup again. */
export const showTourWelcome = () => emit(TOUR_EVENTS.welcome);
export const openDocumentation = () => emit(TOUR_EVENTS.docs);
export const contactSupport = () => emit(TOUR_EVENTS.support);
