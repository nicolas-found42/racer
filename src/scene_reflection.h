#pragma once
#include <array>
#include <bgfx/bgfx.h>
#include <bx/math.h>
#include <cmath>
#include <stdexcept>
#include <utility>

namespace racer {
// Local scene capture, with one face amortized over each frame. The caller
// draws sky/world only into the returned view and destroys this before bgfx
// shutdown.
class SceneReflection {
public:
  struct Face {
    uint16_t view;
    float viewMatrix[16], projection[16];
    float eye[3];
  };

  SceneReflection() {
    for (auto &cube : faces_)
      for (auto &face : cube)
        face = BGFX_INVALID_HANDLE;
    try {
      constexpr uint32_t required = BGFX_CAPS_FORMAT_TEXTURE_CUBE |
                                    BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER |
                                    BGFX_CAPS_FORMAT_TEXTURE_MIP_AUTOGEN;
      if ((bgfx::getCaps()->formats[bgfx::TextureFormat::RGBA16F] & required) !=
              required ||
          !(bgfx::getCaps()->formats[bgfx::TextureFormat::D32F] &
            BGFX_CAPS_FORMAT_TEXTURE_FRAMEBUFFER))
        throw std::runtime_error("scene_reflection_hdr_format_unsupported");
      constexpr uint64_t flags = BGFX_TEXTURE_RT | BGFX_SAMPLER_U_CLAMP |
                                 BGFX_SAMPLER_V_CLAMP | BGFX_SAMPLER_W_CLAMP;
      for (auto &cube : cubes_) {
        cube = bgfx::createTextureCube(size, true, 1,
                                       bgfx::TextureFormat::RGBA16F, flags);
        if (!bgfx::isValid(cube))
          throw std::runtime_error("scene_reflection_cube");
      }
      depth_ =
          bgfx::createTexture2D(size, size, false, 1, bgfx::TextureFormat::D32F,
                                BGFX_TEXTURE_RT | BGFX_TEXTURE_RT_WRITE_ONLY);
      if (!bgfx::isValid(depth_))
        throw std::runtime_error("scene_reflection_depth");
      for (size_t cube = 0; cube < faces_.size(); ++cube) {
        for (uint16_t side = 0; side < 6; ++side) {
          bgfx::Attachment attachments[2];
          // Attachment::_layer selects the cube side, not an array cube index.
          // Generate the complete cube mip pyramid only after the final face.
          // Metal resolves this framebuffer before subsequent views/frames
          // sample it.
          attachments[0].init(cubes_[cube], bgfx::Access::Write, side, 1, 0,
                              side == 5 ? BGFX_ATTACHMENT_AUTO_GEN_MIPS : 0);
          attachments[1].init(depth_, bgfx::Access::Write, 0, 1, 0, 0);
          faces_[cube][side] = bgfx::createFrameBuffer(2, attachments, false);
          if (!bgfx::isValid(faces_[cube][side]))
            throw std::runtime_error("scene_reflection_framebuffer");
        }
      }
    } catch (...) {
      release();
      throw;
    }
  }
  ~SceneReflection() { release(); }
  SceneReflection(const SceneReflection &) = delete;
  SceneReflection &operator=(const SceneReflection &) = delete;
  SceneReflection(SceneReflection &&) = delete;
  SceneReflection &operator=(SceneReflection &&) = delete;

  bgfx::TextureHandle readTexture() const noexcept { return cubes_[read_]; }
  bool ready() const noexcept { return ready_; }

  Face beginFrame(float carX, float carZ, float elevation = 0) {
    if (active_)
      throw std::logic_error("scene_reflection_frame_already_open");
    if (!std::isfinite(carX) || !std::isfinite(carZ) ||
        !std::isfinite(elevation))
      throw std::runtime_error("scene_reflection_eye");
    if (nextFace_ == 0)
      center_ = {carX, elevation + 1.6f, carZ};
    // +X,-X,+Y,-Y,+Z,-Z. Left-handed camera right/up axes match
    // cube sampling sc/tc: (-z,-y),(z,-y),(x,z),(x,-z),(x,-y),(-x,-y).
    constexpr std::array<bx::Vec3, 6> directions{
        {{1, 0, 0}, {-1, 0, 0}, {0, 1, 0}, {0, -1, 0}, {0, 0, 1}, {0, 0, -1}}};
    constexpr std::array<bx::Vec3, 6> up{
        {{0, 1, 0}, {0, 1, 0}, {0, 0, -1}, {0, 0, 1}, {0, 1, 0}, {0, 1, 0}}};
    Face result{};
    result.view = uint16_t(3 + nextFace_);
    const bx::Vec3 eye{center_[0], center_[1], center_[2]};
    const auto direction = directions[nextFace_];
    const bx::Vec3 target{eye.x + direction.x, eye.y + direction.y,
                          eye.z + direction.z};
    bx::mtxLookAt(result.viewMatrix, eye, target, up[nextFace_],
                  bx::Handedness::Left);
    bx::mtxProj(result.projection, 90.f, 1.f, .15f, 900.f,
                bgfx::getCaps()->homogeneousDepth, bx::Handedness::Left);
    for (size_t axis = 0; axis < 3; ++axis)
      result.eye[axis] = center_[axis];
    // Views 1/2 sample the previous complete cube before views 3..8 write
    // the other cube. No face from an incomplete capture becomes visible.
    bgfx::setViewFrameBuffer(result.view, faces_[write_][nextFace_]);
    bgfx::setViewRect(result.view, 0, 0, size, size);
    bgfx::setViewClear(result.view, BGFX_CLEAR_COLOR | BGFX_CLEAR_DEPTH,
                       0x526c87ff, 1.f, 0);
    bgfx::setViewMode(result.view, bgfx::ViewMode::Sequential);
    bgfx::setViewTransform(result.view, result.viewMatrix, result.projection);
    bgfx::touch(result.view);
    active_ = true;
    return result;
  }

  void endFrame() {
    if (!active_)
      throw std::logic_error("scene_reflection_frame_not_open");
    active_ = false;
    if (++nextFace_ == 6) {
      nextFace_ = 0;
      std::swap(read_, write_);
      ready_ = true;
    }
  }

private:
  static constexpr uint16_t size = 256;
  std::array<bgfx::TextureHandle, 2> cubes_{
      {BGFX_INVALID_HANDLE, BGFX_INVALID_HANDLE}};
  bgfx::TextureHandle depth_ = BGFX_INVALID_HANDLE;
  std::array<std::array<bgfx::FrameBufferHandle, 6>, 2> faces_{};
  std::array<float, 3> center_{};
  uint8_t read_ = 0, write_ = 1, nextFace_ = 0;
  bool ready_ = false, active_ = false;

  void release() noexcept {
    for (auto &cube : faces_)
      for (auto &face : cube) {
        if (bgfx::isValid(face))
          bgfx::destroy(face);
        face = BGFX_INVALID_HANDLE;
      }
    if (bgfx::isValid(depth_))
      bgfx::destroy(depth_);
    depth_ = BGFX_INVALID_HANDLE;
    for (auto &cube : cubes_) {
      if (bgfx::isValid(cube))
        bgfx::destroy(cube);
      cube = BGFX_INVALID_HANDLE;
    }
  }
};
} // namespace racer
