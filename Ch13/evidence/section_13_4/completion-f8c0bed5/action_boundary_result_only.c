/* Ch13 diagnostic interposition; forwards every call to the real installed RCL.
 * No fabricated response, server replacement, driver or system modification.
 * Compile against installed Jazzy headers; used only by explicitly owned trials.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <unistd.h>
#include <time.h>
#include <rcl_action/action_client.h>
#include <rcl_action/action_server.h>

static void *resolve(const char *name) {
  void *symbol = dlsym(RTLD_NEXT, name);
  if (!symbol) {
    /* Python extensions may load RCL in a local symbol group. */
    void *library = dlopen("librcl_action.so", RTLD_NOW | RTLD_NOLOAD);
    if (library) symbol = dlsym(library, name);
  }
  return symbol;
}

static void event(const char *name, const void *handle, int64_t seq,
                  const void *uuid, int status, int rc) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  char key[33] = "";
  if (uuid) {
    const unsigned char *bytes = uuid;
    for (int i=0; i<16; ++i) snprintf(key+2*i, 3, "%02x", bytes[i]);
  }
  fprintf(stderr, "CH13_ACTION boundary=%s pid=%d handle=%p seq=%ld uuid=%s status=%d rc=%d mono_ns=%ld\n",
          name, getpid(), handle, seq, key, status, rc, ts.tv_sec*1000000000L+ts.tv_nsec);
}

rcl_ret_t rcl_action_send_result_request(const rcl_action_client_t *c,
                                        const void *req, int64_t *seq) {
  typedef rcl_ret_t (*fn)(const rcl_action_client_t *, const void *, int64_t *);
  fn real = (fn)resolve("rcl_action_send_result_request");
  if (!real) return RCL_RET_ERROR;
  rcl_ret_t rc = real(c, req, seq);
  event("client_send", c, rc == RCL_RET_OK ? *seq : -1, req, -1, rc);
  return rc;
}
rcl_ret_t rcl_action_take_result_request(const rcl_action_server_t *s,
                                        rmw_request_id_t *hdr, void *req) {
  typedef rcl_ret_t (*fn)(const rcl_action_server_t *, rmw_request_id_t *, void *);
  fn real = (fn)resolve("rcl_action_take_result_request");
  if (!real) return RCL_RET_ERROR;
  rcl_ret_t rc = real(s, hdr, req);
  if (rc == RCL_RET_OK) event("server_take", s, hdr->sequence_number, req, -1, rc);
  return rc;
}
rcl_ret_t rcl_action_send_result_response(const rcl_action_server_t *s,
                                         rmw_request_id_t *hdr, void *res) {
  typedef rcl_ret_t (*fn)(const rcl_action_server_t *, rmw_request_id_t *, void *);
  fn real = (fn)resolve("rcl_action_send_result_response");
  if (!real) return RCL_RET_ERROR;
  rcl_ret_t rc = real(s, hdr, res);
  event("server_send", s, hdr->sequence_number, NULL, *(int8_t *)res, rc);
  return rc;
}
rcl_ret_t rcl_action_take_result_response(const rcl_action_client_t *c,
                                         rmw_request_id_t *hdr, void *res) {
  typedef rcl_ret_t (*fn)(const rcl_action_client_t *, rmw_request_id_t *, void *);
  fn real = (fn)resolve("rcl_action_take_result_response");
  if (!real) return RCL_RET_ERROR;
  rcl_ret_t rc = real(c, hdr, res);
  if (rc == RCL_RET_OK) event("client_take", c, hdr->sequence_number, NULL, *(int8_t *)res, rc);
  return rc;
}
