import asyncio

from application.dtos.service_dtos import VoicePipelineServiceRequestDto
from application.services.brain_service import BrainService
from composition_root.config import AppConfig
from domain.console import console_log


def start_internal_pipeline_supervisor(service: BrainService, config: AppConfig) -> asyncio.Task | None:
    if not config.startup_internal_pipeline_enabled:
        console_log("pipeline-supervisor", "startup internal pipeline disabled")
        return None

    console_log(
        "pipeline-supervisor",
        "starting internal startup pipeline supervisor",
        max_text_segments=config.startup_internal_pipeline_max_text_segments,
    )
    return asyncio.create_task(_run_pipeline_forever(service, config))


async def _run_pipeline_forever(service: BrainService, config: AppConfig) -> None:
    run_count = 0
    while True:
        run_count += 1
        try:
            console_log("pipeline-supervisor", "starting internal pipeline run", run=run_count)
            response = await service.run_voice_pipeline(
                VoicePipelineServiceRequestDto(
                    max_text_segments=config.startup_internal_pipeline_max_text_segments,
                )
            )
            console_log(
                "pipeline-supervisor",
                "internal pipeline run completed",
                run=run_count,
                success=response.success,
                text_segments_forwarded=response.text_segments_forwarded,
            )
        except asyncio.CancelledError:
            console_log("pipeline-supervisor", "internal pipeline supervisor cancelled")
            raise
        except Exception as exc:
            console_log("pipeline-supervisor", "internal pipeline run failed", run=run_count, error=str(exc))

        console_log(
            "pipeline-supervisor",
            "waiting before internal pipeline restart",
            seconds=config.startup_internal_pipeline_restart_delay_seconds,
        )
        await asyncio.sleep(config.startup_internal_pipeline_restart_delay_seconds)

