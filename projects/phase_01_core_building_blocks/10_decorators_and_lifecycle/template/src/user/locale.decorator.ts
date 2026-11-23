// TODO(1.10) Task 2
// A second parameter decorator, one that needs no argument: @Locale().
// It reads the request header "accept-language" and returns the language of the FIRST tag, lower-cased,
// without region or quality: 'fr-CH,fr;q=0.9,en;q=0.8' gives 'fr', 'EN-us' gives 'en'.
// A missing or empty header gives 'en'.
// Same tool as Task 1: createParamDecorator. When the decorator takes no data, the factory simply ignores
// its first argument.
export const Locale = (): ParameterDecorator => () => {};
