# frozen_string_literal: true

require "open3"
require "json"
require 'base64'
require 'securerandom'
require_relative "../rb_common/rb_common"

class ThumbnailFrameMatcher
  PTS_TIME_REGEX = /pts_time:([\d\.]+)/

  def initialize(video_path:, image_path:)
    @temporary_directory = "#{generated_path}tmp"
    @logger = Stash::Logger
    @logger.trace("Initializing ThumbnailFrameMatcher class")
    @config = Config::Stash
    @temporary_image = temporary_image_path
    @extracted_frame = temporary_image_path(extracted: true)
    @video = video_path.strip
    @image = image_path.strip
    @video_resolution = get_resolution(file: @video)
    @image_resolution = get_resolution(file: @image)
    @video_duration = get_video_duration
    ensure_correct_image_resolution
    @output = {}
  end

  def run_matcher
    95.step(70, -5) do |level|
      frame = find_frame(match_percentage: level)
      unless frame.nil?
        @logger.info("Found matching frame with match percentage level #{level}")
        extract_frame(frame)
        base64_encode_extracted_frame
        break
      end
    end

  ensure
    cleanup_image_files
    @logger.info("No matching frame found.") if @output.empty?
    puts(JSON.dump(@output))
  end

  private

  def generated_path
    @generated_path ||= GraphQL::Stash.new.configuration["general"]["generatedPath"]
  end

  def temporary_image_path(extracted: false)
    uuid = SecureRandom.uuid
    unless extracted
      @logger.trace("Generating random temporary path for temporary image storage")
      "#{@temporary_directory}tmp_image_#{uuid}.jpg"
    else
      @logger.trace("Generating random temporary path for extracted frame storage")
      "#{@temporary_directory}extracted_frame_#{uuid}.jpg"
    end
  end

  def wget_file(file:)
    @logger.trace("Getting current screenshot image from Stash")
    "wget --header=\"ApiKey: #{@config.api_key}\" -O- #{file} | "
  end

  def get_resolution(file:)
    @logger.trace("Getting resolution of #{file}")
    command = "ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 -i"

    if file.match?(/^http/)
      output = Open3.capture3("#{wget_file(file: file)} #{command} -")
    else
      output = Open3.capture3("#{command} \"#{file}\"")
    end
    resolution = output.first.chomp

    return @logger.error("Invalid resolution for #{file}") unless valid_resolution?(resolution)

    resolution
  end

  def valid_resolution?(resolution)
    @logger.trace("Ensuring valid resolution format in FFPROBE output")
    resolution.match?(/^\d+x\d+$/)
  end

  def get_video_duration
    @logger.trace("Getting video duration")
    output = Open3.capture3("ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"#{@video}\"")
    duration = output.first.chomp

    return @logger.error("Invalid duration for #{@video}") unless valid_duration?(duration)

    duration.to_i
  end

  def valid_duration?(duration)
    @logger.trace("Ensuring valid duration format in FFPROBE output")
    duration.match?(/^\d+\.\d+$/)
  end

  def ensure_correct_image_resolution
    return @logger.debug("Resolutions of video and image match") if resolutions_match?

    @logger.debug("Changing image to matching resolution")

    Open3.capture3("#{wget_file(file: @image)} ffmpeg -y -i - -vf scale=#{@video_resolution} #{@temporary_image}")
    return @logger.error("Temporary image not created") unless File.exist?(@temporary_image)

    @image = @temporary_image
  end

  def resolutions_match?
    @logger.trace("Checking for image resolution match")
    @video_resolution == @image_resolution
  end

  def find_frame(match_percentage:)
    @logger.debug("Looking for frame match with match percentage level #{match_percentage}")
    output = Open3.capture3(
      "ffmpeg -ss 0 -t #{@video_duration} -copyts -i \"#{@video}\" -i \"#{@image}\" "\
      "-filter_complex \"[0]extractplanes=y[v];[1]extractplanes=y[i];[v][i]blend=difference,blackframe=0,"\
      "metadata=select:key=lavfi.blackframe.pblack:value=#{match_percentage}:function=greater,"\
      "trim=duration=0.0001,metadata=print:file=-\" -an -v 0 -vsync 0 -f null -"
    )

    if pts_found?(output)
      pts = extract_pts(output)
    else
      pts = nil
    end

    pts
  end

  def pts_found?(output)
    @logger.trace("Checking for PTS in FFMPEG output")
    output.first.match?(PTS_TIME_REGEX)
  end

  def extract_pts(output)
    @logger.trace("Extracting PTS from FFMPEG output")
    output.first.match(PTS_TIME_REGEX)[1]
  end

  def extract_frame(frame)
    @logger.trace("Extracting matched frame from video")
    Open3.capture3("ffmpeg -y -ss #{frame} -i \"#{@video}\" -frames:v 1 -q:v 2 #{@extracted_frame}")
  end

  def base64_encode_extracted_frame
    @logger.trace("Encoding extracted frame to base64")
    @output["image"] = 'data:image/jpeg;base64,' + Base64.strict_encode64(File.open(@extracted_frame, "rb").read)
  end

  def cleanup_image_files
    @logger.trace("Cleaning up temporary files")
    [@temporary_image, @extracted_frame].each do |file_path|
      next unless File.exist?(file_path)
      File.delete(file_path)
    end
  end
end

scene_fragment = JSON.parse(STDIN.read)
scene_details = GraphQL::Stash.new.get_scene(scene_fragment["id"])
video_path = scene_details["path"]
image_path = scene_details["paths"]["screenshot"]
matcher = ThumbnailFrameMatcher.new(video_path: video_path, image_path: image_path)

matcher.run_matcher
