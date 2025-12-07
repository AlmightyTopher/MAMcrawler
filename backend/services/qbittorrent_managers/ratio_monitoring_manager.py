"""
Ratio Monitoring Manager

Handles monitoring and optimization of seeding ratio and efficiency.
Calculates point generation and provides recommendations.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class RatioMonitoringManager:
    """
    Manager for ratio monitoring and seeding optimization.

    Encapsulates all ratio-related operations including:
    - Optimizing seeding vs downloading allocation
    - Calculating point generation estimates
    - Analyzing upload efficiency
    - Providing optimization recommendations

    Args:
        monitor_service: Reference to parent QBittorrentMonitorService
    """

    def __init__(self, monitor_service):
        """Initialize ratio manager with monitor service reference."""
        self.monitor_service = monitor_service
        self.last_optimization = None

    async def optimize_seeding_allocation(self) -> Dict[str, Any]:
        """
        Optimize seeding allocation for maximum point generation.

        Strategy:
        - Maintain 70% seeding, 30% downloading ratio
        - Adjust qBittorrent seeding slots based on optimal ratio
        - Maximize upload bandwidth usage

        Returns:
            Dictionary with optimization metrics and actions taken

        Example:
            >>> result = await manager.optimize_seeding_allocation()
            >>> print(f"Optimal seeding slots: {result['optimal_seeding']}")
        """
        try:
            state_manager = self.monitor_service.state_manager
            total_seeding = state_manager.get_seeding_count()
            total_downloading = state_manager.get_downloading_count()
            total_torrents = total_seeding + total_downloading

            # Calculate optimal ratio (70% seeding, 30% downloading)
            if total_torrents > 0:
                optimal_seeding = max(1, int(total_torrents * 0.7))
                optimal_downloading = total_torrents - optimal_seeding
            else:
                optimal_seeding = 0
                optimal_downloading = 0

            result = {
                'current_seeding': total_seeding,
                'current_downloading': total_downloading,
                'total_torrents': total_torrents,
                'optimal_seeding': optimal_seeding,
                'optimal_downloading': optimal_downloading,
                'seeding_percentage': (total_seeding / total_torrents * 100) if total_torrents > 0 else 0,
                'action_taken': 'no_change',
                'timestamp': datetime.utcnow().isoformat()
            }

            # Adjust qBittorrent seeding limit if needed
            if self.monitor_service.qb_client and optimal_seeding > 0:
                try:
                    current_limit = await self.monitor_service.qb_client.get_seeding_limit()

                    if current_limit != optimal_seeding:
                        await self.monitor_service.qb_client.set_seeding_limit(optimal_seeding)
                        result['action_taken'] = 'adjusted_seeding_limit'
                        result['previous_limit'] = current_limit
                        logger.info(
                            f"Optimized seeding allocation: "
                            f"{current_limit} -> {optimal_seeding} slots"
                        )

                except Exception as e:
                    logger.warning(f"Failed to adjust seeding limit: {e}")

            self.last_optimization = datetime.utcnow()
            logger.info(
                f"Seeding optimization: "
                f"Current: {total_seeding}:{total_downloading}, "
                f"Optimal: {optimal_seeding}:{optimal_downloading}"
            )

            return result

        except Exception as e:
            logger.error(f"Error optimizing seeding allocation: {e}", exc_info=True)
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def calculate_point_generation(self) -> Dict[str, Any]:
        """
        Calculate estimated point generation from current seeding activity.

        Uses upload speed and number of seeders to estimate points/hour.
        Model: 1 MB/s = 1 point/second (conservative estimate)

        Returns:
            Dictionary with point generation metrics

        Example:
            >>> metrics = await manager.calculate_point_generation()
            >>> print(f"Estimated: {metrics['estimated_points_per_hour']:.0f} points/hour")
        """
        try:
            state_manager = self.monitor_service.state_manager
            seeding_torrents = state_manager.seeding_torrents

            total_seeders = len(seeding_torrents)
            total_upload_speed = 0
            high_priority_count = 0

            # Calculate upload speed and priority stats
            for torrent in seeding_torrents:
                speed = torrent.get('upspeed', 0)
                total_upload_speed += speed

                # Count high-priority seeders (ratio < 2.0)
                ratio = torrent.get('ratio', 1.0)
                if ratio < 2.0:
                    high_priority_count += 1

            # Estimate points per hour
            # Model: 1 MB/s upload = 1 point/second = 3600 points/hour
            upload_mbps = total_upload_speed / (1024 * 1024)
            estimated_points_per_hour = upload_mbps * 3600

            result = {
                'total_seeders': total_seeders,
                'high_priority_seeders': high_priority_count,
                'total_upload_speed': total_upload_speed,
                'upload_mbps': round(upload_mbps, 2),
                'estimated_points_per_hour': round(estimated_points_per_hour, 2),
                'estimated_points_per_day': round(estimated_points_per_hour * 24, 0),
                'timestamp': datetime.utcnow().isoformat()
            }

            logger.info(
                f"Point generation: "
                f"{total_seeders} seeders, "
                f"{upload_mbps:.2f} MB/s upload, "
                f"{estimated_points_per_hour:.0f} points/hour"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating point generation: {e}", exc_info=True)
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def get_upload_efficiency(self) -> Dict[str, Any]:
        """
        Calculate upload efficiency metrics.

        Analyzes bandwidth utilization and per-torrent efficiency.

        Returns:
            Dictionary with efficiency metrics

        Example:
            >>> efficiency = await manager.get_upload_efficiency()
            >>> print(f"Avg per torrent: {efficiency['avg_upload_per_torrent']:.2f} MB/s")
        """
        try:
            state_manager = self.monitor_service.state_manager
            seeding_torrents = state_manager.seeding_torrents

            if not seeding_torrents:
                return {
                    'total_seeders': 0,
                    'efficiency_metrics': 'no_seeders',
                    'timestamp': datetime.utcnow().isoformat()
                }

            total_upload = sum(t.get('upspeed', 0) for t in seeding_torrents)
            avg_upload_per_torrent = total_upload / len(seeding_torrents) if seeding_torrents else 0
            avg_upload_mbps = avg_upload_per_torrent / (1024 * 1024)

            result = {
                'total_seeders': len(seeding_torrents),
                'total_upload': total_upload,
                'total_upload_mbps': round(total_upload / (1024 * 1024), 2),
                'avg_upload_per_torrent': avg_upload_per_torrent,
                'avg_upload_per_torrent_mbps': round(avg_upload_mbps, 4),
                'timestamp': datetime.utcnow().isoformat()
            }

            logger.debug(
                f"Upload efficiency: "
                f"{result['avg_upload_per_torrent_mbps']:.4f} MB/s per torrent"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating upload efficiency: {e}", exc_info=True)
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def analyze_seeding_strategy(self) -> Dict[str, Any]:
        """
        Analyze current seeding strategy and provide recommendations.

        Evaluates point generation, efficiency, and allocation to recommend optimizations.

        Returns:
            Dictionary with analysis and recommendations

        Example:
            >>> analysis = await manager.analyze_seeding_strategy()
            >>> print(f"Recommendation: {analysis['recommendation']}")
        """
        try:
            efficiency = await self.get_upload_efficiency()
            points = await self.calculate_point_generation()
            optimization = await self.optimize_seeding_allocation()

            recommendation = "maintain_current_strategy"
            reasoning = []

            # Analyze upload efficiency
            if 'error' not in efficiency and efficiency.get('total_seeders', 0) > 0:
                avg_mbps = efficiency.get('avg_upload_per_torrent_mbps', 0)

                if avg_mbps < 0.01:
                    recommendation = "reduce_active_seeders"
                    reasoning.append("Average upload per torrent is very low (<0.01 MB/s)")
                elif avg_mbps > 1.0:
                    recommendation = "increase_active_seeders"
                    reasoning.append("Average upload per torrent is high (>1.0 MB/s)")

            # Analyze seeding allocation
            if 'error' not in optimization:
                seeding_pct = optimization.get('seeding_percentage', 0)

                if seeding_pct < 60:
                    reasoning.append("Seeding allocation below optimal 70%")
                elif seeding_pct > 80:
                    reasoning.append("Seeding allocation above optimal 70%")

            result = {
                'recommendation': recommendation,
                'reasoning': reasoning,
                'current_seeders': efficiency.get('total_seeders', 0),
                'current_upload_mbps': efficiency.get('total_upload_mbps', 0),
                'estimated_points_per_hour': points.get('estimated_points_per_hour', 0),
                'seeding_percentage': optimization.get('seeding_percentage', 0),
                'timestamp': datetime.utcnow().isoformat()
            }

            logger.info(f"Seeding strategy analysis: {recommendation}")

            return result

        except Exception as e:
            logger.error(f"Error analyzing seeding strategy: {e}", exc_info=True)
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    def get_last_optimization_time(self) -> Optional[datetime]:
        """Get timestamp of last seeding optimization."""
        return self.last_optimization
