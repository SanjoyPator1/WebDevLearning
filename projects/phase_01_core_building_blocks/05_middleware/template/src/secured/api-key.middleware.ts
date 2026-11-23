// TODO(1.5) Task 6
// Write a class middleware that protects a route with an API key.
//   - the request header "x-api-key" must equal "secret"
//   - if it does, let the request continue
//   - if it does not (missing or wrong), answer 401 with the JSON body
//     { "message": "invalid api key" } yourself, and do NOT continue: the handler must not run
// A middleware that neither answers nor continues leaves the request hanging forever. A
// middleware that answers AND continues makes the handler run for a request that was already
// answered. Pick exactly one path in each case.
// The module (secured.module.ts) is given and already applies this class to SecuredController.
export class ApiKeyMiddleware {}
