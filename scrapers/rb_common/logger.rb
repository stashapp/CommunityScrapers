# frozen_string_literal: true

module Stash
  class Logger
    class << self
      # Log messages sent from a script scraper instance are transmitted via stderr
      # and are encoded with a prefix consisting of the special character SOH, then
      # the log level (one of t, d, i, w, or e - corresponding to trace, debug, info,
      # warning and error levels respectively), then the special character STX.

      def trace(text)
        log("t", text)
      end

      def debug(text)
        log("d", text)
      end

      def info(text)
        log("i", text)
      end

      def warning(text)
        log("w", text)
      end

      def error(text)
        log("e", text)
      end

      private

      def log(level, text)
        level_char = control_wrap(level)

        # I'm not sure what case is covered by the image part of this regex, but it
        # was present in the py_common version so I've included it.
        text.dup.gsub!(/data:image.+?;base64(.+?')/) { |match| text }

        text.split("\n").each { |message| STDERR.puts(level_char + message) }
      end

      def control_wrap(level)
        # Wraps the string between the SOH and STX control characters
        "\x01#{level}\x02"
      end
    end
  end
end
